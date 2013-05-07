from logging import Handler
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class ResultListItemDelegate(QStyledItemDelegate, object):
    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        option.text = ''
        style = QApplication.style() if not option.widget else option.widget.style()

        style.drawControl(QStyle.CE_ItemViewItem, option, painter)

        model = index.model()
        document = QTextDocument()
        document.setHtml(QString('<p>Distance: <b>%1</b></p>'
                                 '<p>%2</p>')
                                .arg(model.data(index,
                                                Qt.DisplayRole).toPyObject())
                                .arg(model.data(index,
                                                Qt.UserRole).toPyObject()))

        painter.save() # start painting

        painter.setClipRect(option.rect)

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, option)

        context = QAbstractTextDocumentLayout.PaintContext()
        context.palette = option.palette
        if option.state & QStyle.State_Selected:
            if option.state & QStyle.State_Active:
                context.palette.setCurrentColorGroup(QPalette.Active)
            else:
                context.palette.setCurrentColorGroup(QPalette.Inactive)
            context.palette.setBrush(QPalette.Text,
                                     context.palette.highlightedText())
            context.palette.setBrush(QPalette.Background,
                                     context.palette.highlight())
        elif option.state & QStyle.State_MouseOver:
            context.palette.setCurrentColorGroup(QPalette.Inactive)
            context.palette.setBrush(QPalette.Background,
                                     context.palette.highlight())
        elif not option.state & QStyle.State_Enabled:
            context.palette.setCurrentColorGroup(QPalette.Disabled)

        painter.translate(textRect.x(),
                          textRect.y() + (textRect.height() - document.size().height()) / 2)

        document.documentLayout().draw(painter, context)

        painter.restore() # painting completed



class Counter(object):
    def __init__(self):
        self.cnt = 0

    def inc(self):
        self.cnt += 1

    def __ge__(self, other):
        return self.cnt >= other



class ResultListModel(QAbstractListModel, object):
    def __init__(self, img_size=(120, 90), data=None, parent=None):
        super(ResultListModel, self).__init__(parent)
        self._data = data if data else []
        self.img_size = img_size


    def append(self, buf, dist, fn):
        self._data.append((buf, dist, fn))


    def rowCount(self, parent=QModelIndex(), *args, **kwargs):
        return len(self._data)


    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return QVariant()

        buf, dist, fn = self._data[index.row()]
        if role == Qt.DecorationRole:
            pix = QPixmap()
            pix.loadFromData(buf)
            return pix.scaled(*self.img_size)
        elif role == Qt.DisplayRole:
            return QVariant(dist)
        elif role == Qt.UserRole:
            return QVariant(fn)

        return QVariant()


    def sort(self, by=None, order=None):
        self._data.sort(key=lambda (_, dist, __): dist)



class ImageWidget(QWidget, object):
    def __init__(self, parent, (min_h, min_w)=(180, 240)):
        super(ImageWidget, self).__init__(parent)
        self.initUI(min_h, min_w)


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.picture)


    def initUI(self, min_h, min_w):
        self.min_height = min_h
        self.min_width = min_w
        self.setMinimumHeight(min_h)
        self.setMinimumWidth(min_w)

        self.picture = self.gen_null_pixmap()
        self.update()


    def gen_null_pixmap(self):
        pixmap = QPixmap(self.min_width, self.min_height)
        pixmap.fill(QColor('green'))

        return pixmap


    def loadImageFromPath(self, path=None):
        self.picture = QPixmap(path)
        self.picture = self.picture.scaled(self.min_width, self.min_height)

        if self.picture.isNull():
            self.picture = self.gen_null_pixmap()
        self.update()


    def loadImageFromBuffer(self, buf):
        self.picture = QPixmap()
        self.picture.loadFromData(buf)
        self.picture = self.picture.scaled(self.min_width ,self.min_height)

        if self.picture.isNull():
            self.picture = self.gen_null_pixmap()
        self.update()



class LoggerHandler(Handler):
    def __init__(self, logger_widget):
        self.logger_widget = logger_widget
        super(LoggerHandler, self).__init__()


    def emit(self, record):
        self.logger_widget.emit(SIGNAL('newLog(QString)'), self.format(record).decode('utf-8'))



