# coding:utf-8
import requests
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QWidget, QGridLayout, QSizePolicy, QPushButton
)
from ..common.config import cfg


class CoverLoader(QThread):
    loaded = Signal(bytes)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        resp = None
        try:
            resp = requests.get(self.url, timeout=10)
            self.loaded.emit(resp.content)
        except Exception:
            self.loaded.emit(b'')
        finally:
            if resp is not None:
                resp.close()


class BookDetailDialog(QDialog):
    sig_download = Signal(list)

    def __init__(self, book, parent=None):
        super().__init__(parent)
        self.book = book
        self.setWindowTitle("书籍详情")
        self.setMinimumSize(500, 600)
        self._initUI()

    def _initUI(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout(content)

        coverLabel = QLabel()
        coverLabel.setAlignment(Qt.AlignCenter)
        coverLabel.setFixedHeight(250)
        coverLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        coverLabel.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        layout.addWidget(coverLabel)

        cover_url = self.book.get('cover', '') or self.book.get('coverUrl', '')
        if cover_url:
            self._loadCover(cover_url, coverLabel)

        grid = QGridLayout()
        grid.setSpacing(8)

        fields = [
            ("书名:", self.book.get('title', '')),
            ("作者:", self.book.get('author', '')),
            ("出版社:", self.book.get('publisher', '')),
            ("年份:", str(self.book.get('year', ''))),
            ("页数:", str(self.book.get('pages', ''))),
            ("语言:", self.book.get('language', '')),
            ("格式:", self.book.get('extension', '')),
            ("文件大小:", self.book.get('filesizeString', '')),
            ("Book ID:", str(self.book.get('id', ''))),
            ("Hash:", self.book.get('hash', '')),
        ]

        for r, (label_text, value) in enumerate(fields):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: bold;")
            val = QLabel(str(value))
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(lbl, r, 0)
            grid.addWidget(val, r, 1)

        layout.addLayout(grid)

        desc = self.book.get('description', '') or self.book.get('desc', '')
        if desc:
            descLabel = QLabel("简介:")
            descLabel.setStyleSheet("font-weight: bold; margin-top: 8px;")
            layout.addWidget(descLabel)
            descText = QLabel(desc)
            descText.setWordWrap(True)
            descText.setTextInteractionFlags(Qt.TextSelectableByMouse)
            descText.setStyleSheet("border: 1px solid #ccc; padding: 6px; background: #fafafa;")
            layout.addWidget(descText)

        layout.addStretch()
        scroll.setWidget(content)

        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(scroll)

        btnLayout = QHBoxLayout()
        btnLayout.addStretch()
        downloadBtn = QPushButton("下载书籍")
        downloadBtn.setMinimumWidth(120)
        downloadBtn.clicked.connect(self._onDownload)
        btnLayout.addWidget(downloadBtn)
        btnLayout.addStretch()
        mainLayout.addLayout(btnLayout)

    def _onDownload(self):
        book = self.book
        self.sig_download.emit([
            book.get('id'),
            book.get('hash'),
            book.get('title'),
            book.get('extension'),
            book.get('filesize'),
            book.get('year', ''),
            book.get('author', '')
        ])
        self.accept()

    def _loadCover(self, url, label):
        if url.startswith('/'):
            url = f'https://{cfg.host}{url}'
        loader = CoverLoader(url, self)
        loader.loaded.connect(lambda data, lbl=label: self._applyCover(data, lbl))
        loader.finished.connect(loader.deleteLater)
        loader.start()

    def _applyCover(self, data, label):
        if not data:
            label.setText("封面加载失败")
            return
        img = QImage()
        if not img.loadFromData(data):
            label.setText("封面加载失败")
            return
        pixmap = QPixmap.fromImage(img)
        scaled = pixmap.scaled(180, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)
