# coding:utf-8
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGroupBox,
    QCheckBox, QSpinBox, QPushButton, QLabel, QFileDialog, QLineEdit,
    QDialog, QDialogButtonBox
)
from ..common.config import cfg, VERSION, YEAR, FileNameTemplates


class SettingPage(QWidget):
    def __init__(self):
        super().__init__()
        self._initUI()

    def _initUI(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)

        self._createSearchGroup(layout)
        self._createFileNameGroup(layout)
        self._createHostGroup(layout)
        self._createAboutGroup(layout)

        layout.addStretch()
        scroll.setWidget(content)

        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(scroll)

    def _createSearchGroup(self, parentLayout):
        group = QGroupBox("搜索&下载设置")
        layout = QVBoxLayout(group)

        row1 = QHBoxLayout()
        self.skipRepeatFiles = QCheckBox("跳过重名文件")
        self.skipRepeatFiles.setChecked(cfg.skipRepeatFiles)
        self.skipRepeatFiles.stateChanged.connect(lambda s: cfg.set("skipRepeatFiles", Qt.CheckState(s) == Qt.Checked))
        row1.addWidget(self.skipRepeatFiles)
        row1.addStretch()
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("每页显示数量:"))
        self.searchNums = QSpinBox()
        self.searchNums.setRange(50, 200)
        self.searchNums.setValue(cfg.searchNums)
        self.searchNums.valueChanged.connect(lambda v: cfg.set("searchNums", v))
        row2.addWidget(self.searchNums)
        row2.addStretch()
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("下载保存路径:"))
        self.downloadFolderLabel = QLabel(cfg.downloadFolder)
        self.downloadFolderLabel.setStyleSheet("border: 1px solid #ccc; padding: 2px;")
        row3.addWidget(self.downloadFolderLabel, 1)
        self.folderBtn = QPushButton("选择文件夹")
        self.folderBtn.clicked.connect(self._onDownloadFolderClicked)
        row3.addWidget(self.folderBtn)
        layout.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("最大并发下载数:"))
        self.maxThreads = QSpinBox()
        self.maxThreads.setRange(1, 50)
        self.maxThreads.setValue(cfg.maxDownloadThreads)
        self.maxThreads.valueChanged.connect(lambda v: cfg.set("maxDownloadThreads", v))
        row4.addWidget(self.maxThreads)
        row4.addStretch()
        layout.addLayout(row4)

        parentLayout.addWidget(group)

    def _createFileNameGroup(self, parentLayout):
        group = QGroupBox("文件名设置")
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel("文件名模板:"))
        self.fileNameLabel = QLabel(cfg.fileNamePattern)
        self.fileNameLabel.setStyleSheet("border: 1px solid #ccc; padding: 2px;")
        layout.addWidget(self.fileNameLabel, 1)
        self.templateBtn = QPushButton("选择模板")
        self.templateBtn.clicked.connect(self._onFileNameCardClicked)
        layout.addWidget(self.templateBtn)

        parentLayout.addWidget(group)

    def _createHostGroup(self, parentLayout):
        group = QGroupBox("服务器设置")
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel("Z-Library 主机地址:"))
        self.hostLabel = QLabel(cfg.host)
        self.hostLabel.setStyleSheet("border: 1px solid #ccc; padding: 2px;")
        layout.addWidget(self.hostLabel, 1)
        self.hostBtn = QPushButton("修改")
        self.hostBtn.clicked.connect(self._onHostCardClicked)
        layout.addWidget(self.hostBtn)

        parentLayout.addWidget(group)

    def _createAboutGroup(self, parentLayout):
        group = QGroupBox("关于")
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel(f"Zlib Downloader v{VERSION} ©{YEAR}"))
        parentLayout.addWidget(group)

    def _onDownloadFolderClicked(self):
        folder = QFileDialog.getExistingDirectory(self, "选择下载文件夹", "./")
        if folder and cfg.downloadFolder != folder:
            cfg.set("downloadFolder", folder)
            self.downloadFolderLabel.setText(folder)

    def _onHostCardClicked(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("设置 Z-Library 主机地址")
        dialog.setMinimumWidth(350)
        vLayout = QVBoxLayout(dialog)
        vLayout.addWidget(QLabel("请输入主机地址（不带 https://）"))
        lineEdit = QLineEdit()
        lineEdit.setText(cfg.host)
        vLayout.addWidget(lineEdit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        vLayout.addWidget(buttons)
        if dialog.exec():
            host = lineEdit.text().strip()
            if host:
                cfg.set("host", host)
                self.hostLabel.setText(host)

    def _onFileNameCardClicked(self):
        from .template_dialog import TemplateDialog
        dialog = TemplateDialog(cfg.fileNamePattern, self)
        if dialog.exec():
            pattern = dialog.getPattern()
            if pattern:
                cfg.set("fileNamePattern", pattern)
                self.fileNameLabel.setText(pattern)
