# coding:utf-8
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QDialogButtonBox
)
from ..common.config import FileNameTemplates


class TemplateDialog(QDialog):
    templateSelected = Signal(str)

    def __init__(self, current_pattern='', parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置文件名模板")
        self.setMinimumWidth(400)
        self.current_pattern = current_pattern
        self._initUI()

    def _initUI(self):
        layout = QVBoxLayout(self)

        hint = QLabel("可用变量:")
        layout.addWidget(hint)

        varLayout = QHBoxLayout()
        for var, label in [('%title%', '书名'), ('%year%', '年份'), ('%author%', '作者')]:
            btn = QPushButton(label)
            btn.setFixedWidth(80)
            btn.clicked.connect(lambda checked, v=var: self._insertVar(v))
            varLayout.addWidget(btn)
        varLayout.addStretch()
        layout.addLayout(varLayout)

        self.lineEdit = QLineEdit()
        self.lineEdit.setText(self.current_pattern)
        layout.addWidget(self.lineEdit)

        self.presetList = QListWidget()
        for name, pattern in FileNameTemplates:
            self.presetList.addItem(name)
        self.presetList.itemDoubleClicked.connect(self._onPresetClicked)
        self.presetList.setMinimumHeight(150)
        layout.addWidget(self.presetList)

        tip = QLabel("操作说明: 点击变量按钮插入变量，双击预设模板快速填入")
        tip.setStyleSheet("color: gray; font-size: 12px;")
        tip.setFixedHeight(20)
        layout.addWidget(tip)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _onPresetClicked(self, item):
        row = self.presetList.row(item)
        if 0 <= row < len(FileNameTemplates):
            _, pattern = FileNameTemplates[row]
            self.lineEdit.setText(pattern)

    def _insertVar(self, var):
        cursor = self.lineEdit.cursorPosition()
        text = self.lineEdit.text()
        text = text[:cursor] + var + text[cursor:]
        self.lineEdit.setText(text)
        self.lineEdit.setCursorPosition(cursor + len(var))

    def getPattern(self):
        return self.lineEdit.text()
