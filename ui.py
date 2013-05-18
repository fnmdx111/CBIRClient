# encoding: utf-8
from collections import deque
import os

import sys
import threading
import timeit
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from requests import ConnectionError
from libs.core import ClientCore
import numpy as np
from libs.ui_comp import ResultListItemDelegate,\
                         ResultListModel,\
                         Counter, ImageWidget, LoggerHandler,\
                         ColoredFormatter


class SecureRetrievalUI(QDialog, object):
    def __init__(self):
        super(SecureRetrievalUI, self).__init__()

        self.setup_misc()

        self.setup_layout()
        self.setup_log_dialog()
        self.connect(self, SIGNAL('results_prepared'), self._results_prepared)
        self.connect(self, SIGNAL('showCriticalBox'), self.show_critical_box)
        self.connect(self, SIGNAL('unlock_buttons()'), self.unlock_buttons)

        self.resize(0, 550)
        self.setMaximumWidth(508)

        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint)
        self.setWindowTitle(u'Secure Image Retrieval Client (powered by 武汉大学对不队)')

        self.asynchronous_login()


    def setup_misc(self):
        self.last_dir_path = ''
        self.result_path = 'results'

        self.logged_in = False
        self.retrieve_block = False

        self.max_result_count = 10

        key = np.float64(.7000000000000001), np.float64(3.6000000000000001), 1
        self.core = ClientCore((key, key, key))


    def setup_log_dialog(self):
        self.log_widget = QTextBrowser()

        handler = LoggerHandler(self.log_widget)
        handler.setFormatter(ColoredFormatter(
            fmt='%(asctime)s %(levelname)s %(message)s',
            colors={'asctime': lambda _: 'blue',
                    'levelname': lambda lvl:
                            ColoredFormatter.gen_colorscheme()[lvl]},
            datefmt='%m/%dT%H:%M:%S'
        ))
        self.core.logger.addHandler(handler)

        self.connect(self.log_widget, SIGNAL('newLog(QString)'), self.new_log)

        dialog = QDialog(self)

        dialog.setWindowTitle(u'Log')
        dialog.resize(400, 200)
        dialog.move(400, 200)

        layout = QVBoxLayout(dialog)
        layout.addWidget(self.log_widget)
        dialog.setLayout(layout)

        self.dialog = dialog


    def show_log_dialog(self):
        if self.dialog.isVisible():
            self.dialog.hide()
        else:
            self.dialog.show()

    def setup_layout(self):
        self.model = ResultListModel()

        image_list_view = QListView()
        image_list_view.setModel(self.model)
        image_list_view.setItemDelegate(ResultListItemDelegate())

        self.file_path = QLineEdit(self)

        def add_preview(widget_name):
            preview = ImageWidget(self)
            if widget_name:
                self.__setattr__(widget_name, preview)
            return preview

        def add_button(widget_name, caption, trigger):
            button = QPushButton(caption, self)
            self.connect(button, SIGNAL('clicked()'), trigger)
            self.__setattr__(widget_name, button)
            return button

        self.status_label = QLabel()

        button_box = QHBoxLayout()
        button_box.addWidget(add_button('select_btn', 'Select File', self.select_image))
        button_box.addStretch()
        button_box.addWidget(self.status_label)
        button_box.addWidget(add_button('reconnect_btn', 'Reconnect', self.asynchronous_login))
        button_box.addWidget(add_button('show_log_btn', 'Show Log', self.show_log_dialog))
        button_box.addWidget(add_button('retrieve_btn', 'Retrieve', self.retrieve_image))
        button_box.addWidget(add_button('upload_btn', 'Upload', self.upload_image))
        self.lock_buttons()

        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel('Original image:'), 0, 0)
        grid_layout.addWidget(QLabel('Encrypted image:'), 0, 1)
        grid_layout.addWidget(add_preview('selected_preview'), 1, 0, 1, 1, Qt.AlignCenter)
        grid_layout.addWidget(add_preview('encrypt_preview'), 1, 1, 1, 1, Qt.AlignCenter)
        grid_layout.addWidget(self.file_path, 2, 0, 1, 2)
        grid_layout.addLayout(button_box, 3, 0, 1, 2)
        grid_layout.addWidget(image_list_view, 4, 0, 1, 2)

        self.setLayout(grid_layout)


    def new_log(self, log):
        self.log_widget.append(log)


    def asynchronous_login(self):
        if self.logged_in:
            return

        def _t():
            try:
                r = self.core.init_core()
                if r['status'] == 'ok':
                    self.core.logger.info('connected to server at %s, have fun',
                                          self.core.server_addr)
                    self.emit(SIGNAL('unlock_buttons()'))
                    self.logged_in = True
                else:
                    self.emit(SIGNAL('showCriticalBox'),
                              QString('Initializing'),
                              QString(r['comment']))
            except ConnectionError:
                self.core.logger.critical('cannot connect to server at %s',
                                          self.core.server_addr)
                self.emit(SIGNAL('showCriticalBox'),
                          QString('Initializing'),
                          QString('Seems that there isn\'t any server running on %1.')
                          .arg(self.core.server_addr))

        t = threading.Thread(target=_t)
        t.start()


    def show_critical_box(self, title, text):
        self.show_message_box(QMessageBox.critical, title, text)


    def show_message_box(self, box_type, title, text):
        box_type(self, title, text, 'OK')


    def lock_buttons(self):
        self.retrieve_btn.setEnabled(False)
        self.upload_btn.setEnabled(False)
        self.reconnect_btn.setEnabled(True)


    def unlock_buttons(self):
        self.retrieve_btn.setEnabled(True)
        self.upload_btn.setEnabled(True)
        self.reconnect_btn.setEnabled(False)


    def select_image(self):
        fn = QFileDialog.getOpenFileName(self, 'Open file', self.last_dir_path, 'JPEG files (*.jpg)')

        if not fn:
            return

        self.last_dir_path = os.path.dirname(str(fn))

        self.file_path.setText(fn)
        self.selected_preview.loadImageFromPath(fn)

        self.buf_encrypted = self.core.save_img_m(self.core.enc_img(str(fn)))
        self.encrypt_preview.loadImageFromBuffer(self.buf_encrypted)


    def upload_image(self):
        if not self.file_path.text():
            self.select_image()
        try:
            r = self.core.upload_img(self.buf_encrypted)
            msg = r['status']
            if msg == 'ok':
                self.core.logger.info('file uploaded')
            else:
                self.show_message_box(QMessageBox.critical, 'Upload', r['comment'])
                self.core.logger.critical('file not uploaded due to error')
        except ConnectionError:
            self.show_message_box(QMessageBox.critical, 'Upload', 'Server is unavailable.')
            self.core.logger.critical('server %s is unavailable', self.core.server_addr)
        finally:
            self.file_path.setText('')


    def retrieve_image(self):
        if self.retrieve_block:
            self.show_message_box(QMessageBox.warning,
                                'Retrieve',
                                'Please wait for this request to be finished.')
            return

        if not self.file_path.text():
            self.select_image()
        if not self.file_path.text():
            return

        self.status_label.setText('')
        count = len(self.model._data)
        self.model.beginRemoveRows(QModelIndex(), 0, count - 1)
        while self.model._data:
            self.model._data.pop(0)
        self.model.endRemoveRows()

        def _t():
            try:
                self.retrieve_block = True
                r = self.core.send_img(self.buf_encrypted, max_count=self.max_result_count)
                self.emit(SIGNAL('results_prepared'), r)
            except ConnectionError:
                self.emit(SIGNAL('showCriticalBox'),
                          QString('Retrieve'),
                          QString('Server is unavailable.'))
                self.retrieve_block = False
                self.core.logger.info('server %s is unavailable', self.core.server_addr)

        prepare_result_thread = threading.Thread(target=_t)
        prepare_result_thread.start()

        self.file_path.setText('')


    def _results_prepared(self, r):
        n = min(r['result'], self.max_result_count)
        self.status_label.setText('<font color="blue"><b>'
                                  'fetching...'
                                  '</b></font>')
        self.core.logger.info('results are prepared at server within %s sec, '
                              'waiting for fetching',
                              r['time_elapsed'])
        lock = threading.Lock()

        result_queue = deque()

        def _t(i, counter):
            try:
                data, dist = self.core.parse_result(None)
                self.core.logger.info('got result %s, dist = %s', i, dist)
                if isinstance(dist, basestring):
                    return
                else:
                    result_queue.append((data, dist, i))
            finally:
                with lock:
                    counter.inc()

        counter = Counter()

        start = timeit.default_timer()
        for i in range(n):
            threading.Thread(target=_t, args=(i, counter)).start()

        def _watcher():
            while True:
                if len(result_queue) > 0:
                    data, dist, i = result_queue.pop()

                    dec_img = self.core.dec_img(
                        array=self.core._from_raw_to_grayscale(data)
                    )

                    buf = self.core.save_img_m(dec_img)
                    fn = self.core.write_result(dec_img, i)

                    self.model.beginInsertRows(QModelIndex(), 0, 0)
                    self.model.append(buf, dist, fn)
                    self.core.logger.info('appending thumbnail %s into list',
                                          i)
                    self.model.endInsertRows()
                if counter >= n and len(result_queue) < 1:
                    break

            self.model.sort()
            self.core.logger.info('results sorted by distance')
            self.retrieve_block = False

            self.core.logger.info('image retrieval is done within %s sec',
                                  '%2.5f' % (timeit.default_timer() - start))
            self.status_label.setText('<font color="green"><b>'
                                      '%s'
                                      '</b></font>' % 'done')
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


