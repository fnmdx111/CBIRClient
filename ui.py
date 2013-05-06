# encoding: utf-8
import os

import sys
import threading
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from requests import ConnectionError
from libs.core import ClientCore
import numpy as np
from libs.ui_comp import ResultListItemDelegate, ResultSortProxy, ResultListModel, Counter


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



class SecureRetrievalUI(QDialog, object):
    def __init__(self):
        super(SecureRetrievalUI, self).__init__()
        self.last_dir_path = ''
        self.result_path = 'results'

        self.logged_in = False
        self.retrieve_block = False

        self.max_result_count = 10

        key = np.float64(.7000000000000001), np.float64(3.6000000000000001), 1
        self.core = ClientCore((key, key, key))

        self.image_list_view = QListView()

        self.image_list_view.setItemDelegate(ResultListItemDelegate())

        self.model = ResultListModel()
        self.sort_proxy = ResultSortProxy()
        self.sort_proxy.setSourceModel(self.model)
        self.image_list_view.setModel(self.sort_proxy)

        def add_preview(widget_name):
            preview = ImageWidget(self)
            if widget_name:
                self.__setattr__(widget_name, preview)
            return preview

        self.file_path = QLineEdit(self)

        def add_button(widget_name, caption, trigger):
            button = QPushButton(caption, self)
            self.connect(button, SIGNAL('clicked()'), trigger)
            self.__setattr__(widget_name, button)
            return button

        button_box = QHBoxLayout()
        button_box.addWidget(add_button('select_btn', 'Select File', self.selectFile))
        button_box.addStretch()
        button_box.addWidget(add_button('reconnect_btn', 'Reconnect', self.reconnect))
        button_box.addWidget(add_button('search_btn', 'Search', self.retrieveSimilarFile))
        button_box.addWidget(add_button('upload_btn', 'Upload', self.uploadFile))
        self.lockButtons()

        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel('Original image:'), 0, 0)
        grid_layout.addWidget(QLabel('Encrypted image:'), 0, 1)
        grid_layout.addWidget(add_preview('selected_preview'), 1, 0, 1, 1, Qt.AlignCenter)
        grid_layout.addWidget(add_preview('encrypt_preview'), 1, 1, 1, 1, Qt.AlignCenter)
        grid_layout.addWidget(self.file_path, 2, 0, 1, 2)
        grid_layout.addLayout(button_box, 3, 0, 1, 2)
        grid_layout.addWidget(self.image_list_view, 4, 0, 1, 2)

        self.setLayout(grid_layout)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint)
        self.setWindowTitle(u'Secure Image Retrieval Client (powered by 武汉大学对不队)')

        self.connect(self, SIGNAL('results_prepared'), self._results_prepared)
        self.connect(self, SIGNAL('showCriticalBox(QString, QString)'),
                     lambda title, text: self.showMessageBox(QMessageBox.critical,
                                                             title,
                                                             text))
        self.connect(self, SIGNAL('showWarningBox(QString, QString)'), self.showMessageBox)
        self.connect(self, SIGNAL('unlock_buttons()'), self.unlockButtons)

        self.asynchronous_login()


    def reconnect(self):
        self.asynchronous_login()


    def asynchronous_login(self):
        if self.logged_in:
            return

        def _t():
            try:
                r = self.core.init_core()
                if r['status'] == 'ok':
                    self.emit(SIGNAL('unlock_buttons()'))
                    self.logged_in = True
                else:
                    self.emit(SIGNAL('showCriticalBox(QString, QString)'),
                              QString('Initializing'),
                              QString(r['comment']))
            except ConnectionError:
                self.emit(SIGNAL('showCriticalBox(QString, QString)'),
                          QString('Initializing'),
                          QString('Seems that there isn\'t any server running on %1.')
                          .arg(self.core.server_addr))

        t = threading.Thread(target=_t)
        t.start()


    def showMessageBox(self, box_type, title, text):
        box_type(self, title, text, 'OK')


    def lockButtons(self):
        self.search_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)
        self.reconnect_btn.setEnabled(True)


    def unlockButtons(self):
        self.search_btn.setEnabled(True)
        self.upload_btn.setEnabled(True)
        self.reconnect_btn.setEnabled(False)


    def selectFile(self):
        fn = QFileDialog.getOpenFileName(self, 'Open file', self.last_dir_path, 'JPEG files (*.jpg)')

        if not fn:
            return

        self.last_dir_path = os.path.dirname(str(fn))

        self.file_path.setText(fn)
        self.selected_preview.loadImageFromPath(fn)

        self.buf_encrypted = self.core.save_img_m(self.core.enc_img(str(fn)))
        self.encrypt_preview.loadImageFromBuffer(self.buf_encrypted)


    def uploadFile(self):
        if not self.file_path.text():
            self.selectFile()
        r = self.core.upload_img_raw(self.buf_encrypted)
        msg = r['status']
        if msg == 'ok':
            self.showMessageBox(QMessageBox.information, 'Upload', 'File uploaded.')
        else:
            self.showMessageBox(QMessageBox.critical, 'Upload', r['comment'])


    def retrieveSimilarFile(self):
        if self.retrieve_block:
            self.showMessageBox(QMessageBox.warning,
                                'Retrieve',
                                'Please wait for this request to be finished.')
            return

        if not self.file_path.text():
            self.selectFile()

        count = len(self.model._data)
        self.model.beginRemoveRows(QModelIndex(), 0, count - 1)
        while self.model._data:
            self.model._data.pop(0)
        self.model.endRemoveRows()

        def _t():
            self.retrieve_block = True
            r = self.core.send_img_raw(self.buf_encrypted, max_count=self.max_result_count)
            self.emit(SIGNAL('results_prepared'), r)
        prepare_result_thread = threading.Thread(target=_t)
        prepare_result_thread.start()


    def _results_prepared(self, r):
        n = min(r, self.max_result_count)
        lock = threading.Lock()

        def _t(i, counter):
            data, dist = self.core.parse_result(None)
            fn = self.core.write_result(data, i)

            self.model.beginInsertRows(QModelIndex(), 0, 0)
            self.model.append(fn, dist)
            self.model.endInsertRows()

            with lock:
                counter.inc()

        counter = Counter()
        for i in range(n):
            threading.Thread(target=_t, args=(i, counter)).start()

        def _watcher():
            while counter < n:
                pass
            # self.sort_proxy.sort(0)
            self.model._data.sort(key=lambda (_, dist): dist)
            self.retrieve_block = False
        threading.Thread(target=_watcher).start()


    def closeEvent(self, event):
        if self.logged_in:
            t = threading.Thread(target=lambda: self.core.finalize_core())
            t.start()



if __name__ == '__main__' :
    app = QApplication(sys.argv)
    ui = SecureRetrievalUI()
    ui.show()
    sys.exit(app.exec_())


