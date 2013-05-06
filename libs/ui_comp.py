
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class ResultListItemDelegate(QStyledItemDelegate, object):
    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        option.text = ''
        style = QApplication.style() if not option.widget else option.widget.style()

        style.drawControl(QStyle.CE_ItemViewItem, option, painter)

        document = QTextDocument()
        document.setHtml(QString('<p>Distance: <b>%1</b></p>'
                                 '<p>%2</p>')
                                .arg(index.model().data(index, Qt.DisplayRole).toPyObject())
                                .arg(index.model().data(index, Qt.UserRole).toPyObject()))

        painter.save()

        painter.setClipRect(option.rect)

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, option)

        context = QAbstractTextDocumentLayout.PaintContext()
        context.palette = option.palette
        context.palette.setBrush(QPalette.Background, option.palette.light())
        if option.state & QStyle.State_Selected:
            if option.state & QStyle.State_Active:
                context.palette.setCurrentColorGroup(QPalette.Active)
            else:
                context.palette.setCurrentColorGroup(QPalette.Inactive)
            context.palette.setBrush(QPalette.Text, context.palette.highlightedText())
        elif option.state & QStyle.State_MouseOver:
            context.palette.setBrush(QPalette.Background, context.palette.highlight())
        elif not option.state & QStyle.State_Enabled:
            context.palette.setCurrentColorGroup(QPalette.Disabled)

        painter.translate(textRect.x(),
                          textRect.y() + (textRect.height() - document.size().height()) / 2)

        document.documentLayout().draw(painter, context)

        painter.restore()



class ResultSortProxy(QSortFilterProxyModel, object):
    def lessThan(self, left_index, right_index):
        left_var = left_index.data(Qt.DisplayRole).toPyObject()
        right_var = right_index.data(Qt.DisplayRole).toPyObject()

        return left_var < right_var



class Counter(object):
    def __init__(self):
        self.cnt = 0

    def inc(self):
        self.cnt += 1

    def __lt__(self, other):
        return self.cnt < other



class ResultListModel(QAbstractListModel, object):
    def __init__(self, data=None, parent=None):
        super(ResultListModel, self).__init__(parent)
        self._data = data if data else []


    def append(self, fn, dist):
        self._data.append((fn, dist))


    def rowCount(self, parent=QModelIndex(), *args, **kwargs):
        return len(self._data)


    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return QVariant()

        fn, dist = self._data[index.row()]
        if role == Qt.DecorationRole:
            # TODO remove hard-coded size
            return QPixmap(fn).scaled(120, 90)
        elif role == Qt.DisplayRole:
            return QVariant(dist)
        elif role == Qt.UserRole:
            return QVariant(fn)

        return QVariant()


