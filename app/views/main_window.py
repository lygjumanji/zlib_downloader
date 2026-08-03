# coding:utf-8
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QStackedWidget, QMessageBox, QLabel
)
from PySide6.QtGui import QAction
from .search_page import SearchPage
from .download_page import DownloadPage
from .setting_page import SettingPage
from .account_page import AccountPage


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Zlib Downloader')
        self.resize(900, 700)

        self.searchPage = SearchPage()
        self.searchPage.sig_download_start.connect(self.start_download)

        self.downloadPage = DownloadPage()
        self.downloadPage.finished.connect(self.download_result)
        self.downloadPage.sig_rate_limit.connect(self.msg_rate_limit)
        self.downloadPage.sig_start.connect(self.start_download_msg)

        self.settingPage = SettingPage()
        self.accountPage = AccountPage()

        self.tabWidget = QTabWidget()
        self.tabWidget.addTab(self.searchPage, "搜索")
        self.tabWidget.addTab(self.downloadPage, "下载")
        self.tabWidget.addTab(self.accountPage, "账户")
        self.tabWidget.addTab(self.settingPage, "设置")
        self.setCentralWidget(self.tabWidget)

        self._centerWindow()

    def _centerWindow(self):
        desktop = self.screen().availableGeometry()
        self.move(desktop.width() // 2 - self.width() // 2,
                  desktop.height() // 2 - self.height() // 2)

    def start_download(self, data):
        bookid, hashid, bookname, extension, size, year, author = data
        self.downloadPage.download(bookid, hashid, bookname, extension, size, year, author)

    def start_download_msg(self, title):
        self.statusBar().showMessage(f"开始下载: {title}", 2000)

    def msg_rate_limit(self, e):
        QMessageBox.warning(self, "下载限制", "请求过于频繁，请1分钟后再试")

    def download_result(self, success, bookname):
        if success:
            self.statusBar().showMessage(f"下载完成: {bookname}", 3000)
        else:
            self.statusBar().showMessage(f"下载失败: {bookname}", 3000)

    def closeEvent(self, event):
        try:
            if self.searchPage.searchEngine and self.searchPage.searchEngine.isRunning():
                self.searchPage.searchEngine.quit()
                self.searchPage.searchEngine.wait(2000)
        except RuntimeError:
            pass
        for downloader in self.downloadPage.downloaders[:]:
            try:
                downloader.stop()
                downloader.wait(3000)
            except RuntimeError:
                pass
        event.accept()
