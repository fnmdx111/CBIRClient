# -*- coding: utf-8 -*-
import os

import sys
import threading
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from requests import ConnectionError
from libs.core import ClientCore
import numpy as np


# show image
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



class ImageBox(QWidget):
    def __init__(self, parent, row, col):
        super(ImageBox, self).__init__(parent)
        self.row = row
        self.col = col

        self.initUI()


    def initUI(self):
        self.box = QGridLayout()
        self.widgets = []
        self.labels = []

        for i in range(self.row):
            for j in range(self.col):
                box = QVBoxLayout()

                label = QLabel('%s dist = ' % (i * self.row + j))
                box.addWidget(label)

                tmp = ImageWidget(self)
                box.addWidget(tmp)

                self.widgets.append(tmp)
                self.labels.append(label)

                self.box.addLayout(box, i, j, 1, 1)

        self.setLayout(self.box)



class LoginThread(QThread, object):
    pass



class MainFrame(QDialog, object):
    def __init__(self):
        super(MainFrame, self).__init__()
        self.last_dir_path = ''
        self.image_box_row = 3
        self.image_box_col = 3
        self.max_result_count = self.image_box_row * self.image_box_col

        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)

        key = np.float64(.7000000000000001), np.float64(3.6000000000000001), 1
        self.core = ClientCore((key, key, key))

        self.initUI()

        self.resultPath = 'results'

        def _t():
            try:
                r = self.core.init_core()
                if r['status'] == 'ok':
                    self.unlockButtons()
                else:
                    self.showCriticalBox('Initializing', r['comment'])
            except ConnectionError:
                self.showCriticalBox('Initializing',
                                     'Seems that there isn\'t any server running on %s' % self.core.server_addr)
                pass

        t = threading.Thread(target=_t)
        t.start()


    def showCriticalBox(self, title, text):
        QMessageBox.warning(self, title, text, 'OK')


    def lockButtons(self):
        self.search_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)


    def unlockButtons(self):
        self.search_btn.setEnabled(True)
        self.upload_btn.setEnabled(True)


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
            QMessageBox.information(self, 'Upload', 'File uploaded.', 'OK')
        else:
            QMessageBox.warning(self, 'Upload', r['comment'], 'OK')


    def retrieveSimilarFile(self):
        if not self.file_path.text():
            self.selectFile()

        r = self.core.send_img_raw(self.buf_encrypted, max_count=self.max_result_count)

        results = []
        n = min(r, self.max_result_count)
        for i in range(n):
            results.append(self.core.parse_result(i))

        # results.sort(key=lambda (_, n): n)

        for i in range(n):
            self.image_box.labels[i].setText('%s dist = ' % i)
            self.image_box.widgets[i].loadImageFromPath()

        for i, (data, dist) in enumerate(results):
            self.image_box.labels[i].setText('%s dist = %s' % (i, dist))
            self.image_box.widgets[i].loadImageFromPath(self.core.write_result(data, i))


    def initUI(self):
        self.image_box = ImageBox(self, self.image_box_row, self.image_box_col)

        def add_preview(widget_name):
            preview = ImageWidget(self)
            if widget_name:
                self.__setattr__(widget_name, preview)
            return preview

        preview_box = QVBoxLayout()
        preview_box.addStretch()
        preview_box.addWidget(QLabel('Original image:'))
        preview_box.addWidget(add_preview('selected_preview'))
        preview_box.addWidget(QLabel('Encrypted image:'))
        preview_box.addWidget(add_preview('encrypt_preview'))

        self.file_path = QLineEdit(self)

        def add_button(widget_name, caption, trigger):
            button = QPushButton(caption, self)
            self.connect(button, SIGNAL('clicked()'), trigger)
            # button.clicked.connect(trigger)
            self.__setattr__(widget_name, button)
            return button

        button_box = QHBoxLayout()
        button_box.addWidget(add_button('select_btn', 'Select File', self.selectFile))
        button_box.addStretch()
        button_box.addWidget(add_button('search_btn', 'Search', self.retrieveSimilarFile))
        button_box.addWidget(add_button('upload_btn', 'Upload', self.uploadFile))
        self.lockButtons()

        right_box = QVBoxLayout()
        right_box.addLayout(preview_box)
        right_box.addWidget(self.file_path)
        right_box.addLayout(button_box)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.image_box)
        main_layout.addStretch()
        main_layout.addLayout(right_box)
        self.setLayout(main_layout)

        self.setWindowTitle(u'Secure Image Retrieval Client (powered by 武汉大学对不队)')

        self.show()


    def closeEvent(self, event):
        t = threading.Thread(target=lambda: self.core.finalize_core())
        t.start()



if __name__ == '__main__' :
    app = QApplication(sys.argv)
    frame = MainFrame()
    sys.exit(app.exec_())


