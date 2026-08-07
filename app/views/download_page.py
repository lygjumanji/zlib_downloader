# coding:utf-8
import os
import sys
import subprocess
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QLabel, QPushButton, QMessageBox, QMenu
)
from ..tools.downloader import Downloader
from ..common.config import cfg


class DownloadPage(QWidget):
    finished = Signal(bool, str)
    sig_start = Signal(str)
    sig_rate_limit = Signal(bool)

    def __init__(self):
        super().__init__()
        self.downloaders = []
        self.downloaderMap = {}
        self._pendingDelete = []
        self._initUI()

    def _initUI(self):
        layout = QVBoxLayout(self)

        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(6)
        self.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableWidget.setHorizontalHeaderLabels(["书名", "大小", "进度", "速度", "状态", "操作"])
        self.tableWidget.verticalHeader().hide()
        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tableWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tableWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.tableWidget.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.tableWidget.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.tableWidget.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.tableWidget.setColumnWidth(1, 70)
        self.tableWidget.setColumnWidth(2, 150)
        self.tableWidget.setColumnWidth(3, 80)
        self.tableWidget.setColumnWidth(4, 60)
        self.tableWidget.setColumnWidth(5, 120)
        self.tableWidget.verticalHeader().setDefaultSectionSize(36)
        self.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self._showContextMenu)
        self.tableWidget.cellDoubleClicked.connect(self._onCellDoubleClicked)

        layout.addWidget(self.tableWidget)

    def download(self, bookid, hashid, bookname, extension, size, year='', author=''):
        for d in self.downloaders:
            if d.bookid == bookid and not d._completed:
                QMessageBox.warning(self, "重复下载",
                                    f"《{bookname}》已在下载列表中。")
                return

        max_threads = cfg.maxDownloadThreads
        active_count = sum(1 for d in self.downloaders
                           if d.isRunning() and not d._is_stopped())
        if active_count >= max_threads:
            QMessageBox.warning(self, "下载限制",
                                f"已达到最大并发下载数 {max_threads}，请等待当前下载完成后再试。")
            return

        downloader = Downloader(bookid, hashid, bookname, extension, size, year, author)
        self.downloaders.append(downloader)

        row = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row)

        self.tableWidget.setItem(row, 0, QTableWidgetItem(bookname))

        sizeStr = self._formatSize(size)
        sizeItem = QTableWidgetItem(sizeStr)
        sizeItem.setTextAlignment(Qt.AlignCenter)
        self.tableWidget.setItem(row, 1, sizeItem)

        progressBar = QProgressBar()
        progressBar.setRange(0, 100)
        progressBar.setAlignment(Qt.AlignCenter)
        self.tableWidget.setCellWidget(row, 2, progressBar)

        speedLabel = QLabel("0 KB/s")
        speedLabel.setAlignment(Qt.AlignCenter)
        self.tableWidget.setCellWidget(row, 3, speedLabel)

        statusLabel = QLabel("等待中")
        statusLabel.setAlignment(Qt.AlignCenter)
        self.tableWidget.setCellWidget(row, 4, statusLabel)

        btnWidget = QWidget()
        btnLayout = QHBoxLayout(btnWidget)
        btnLayout.setContentsMargins(2, 2, 2, 2)

        pauseBtn = QPushButton("暂停")
        pauseBtn.setFixedWidth(50)
        pauseBtn.clicked.connect(lambda: self._pauseDownload(downloader, pauseBtn))

        deleteBtn = QPushButton("删除")
        deleteBtn.setFixedWidth(50)
        deleteBtn.clicked.connect(lambda: self._deleteDownload(downloader))

        btnLayout.addWidget(pauseBtn)
        btnLayout.addWidget(deleteBtn)
        self.tableWidget.setCellWidget(row, 5, btnWidget)

        self.downloaderMap[id(downloader)] = {
            'row': row,
            'pauseBtn': pauseBtn,
            'deleteBtn': deleteBtn,
            'statusLabel': statusLabel,
        }

        downloader.sig_down_process.connect(lambda v, pb=progressBar: pb.setValue(v))
        downloader.speed.connect(lambda s, lbl=speedLabel: lbl.setText(f"{s} KB/s"))
        downloader.sig_start.connect(lambda name, lbl=statusLabel: lbl.setText("下载中"))
        downloader.sig_status.connect(lambda s, lbl=statusLabel: lbl.setText(
            '下载中' if s == 'downloading' else '已暂停' if s == 'paused'
            else '已完成' if s == 'completed' else '已停止'
        ))
        downloader.final.connect(lambda ok, name, dl=downloader: self._onFinished(ok, name, dl))
        downloader.sig_rate_limit.connect(lambda: self.sig_rate_limit.emit(True))
        downloader.finished.connect(lambda dl=downloader: self._cleanupThread(dl))

        downloader.start()
        self.sig_start.emit(bookname)

    def _formatSize(self, size):
        if not size:
            return ''
        try:
            size = int(size)
        except (ValueError, TypeError):
            return str(size)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / 1024 / 1024:.1f} MB"
        else:
            return f"{size / 1024 / 1024 / 1024:.2f} GB"

    def _pauseDownload(self, downloader, pauseBtn):
        if downloader.status == 'downloading':
            downloader.pause()
            pauseBtn.setText("继续")
        elif downloader.status == 'paused':
            downloader.resume()
            pauseBtn.setText("暂停")

    def _deleteDownload(self, downloader):
        info = self.downloaderMap.get(id(downloader))
        if not info:
            return

        if downloader._completed:
            self._removeRow(downloader)
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除下载 \"{downloader.raw_title}\" 吗？\n未完成的文件将被删除。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if downloader not in self._pendingDelete:
                self._pendingDelete.append(downloader)
            info['deleteBtn'].setEnabled(False)
            info['statusLabel'].setText("正在停止...")
            downloader.stop()

    def _cleanupThread(self, downloader):
        if downloader in self._pendingDelete:
            self._pendingDelete.remove(downloader)
            self._removeRow(downloader)

    def _syncRows(self, removed_row):
        for data in self.downloaderMap.values():
            if data['row'] > removed_row:
                data['row'] -= 1

    def _onFinished(self, success, bookname, downloader):
        info = self.downloaderMap.get(id(downloader))
        if info:
            info['statusLabel'].setText('完成' if success else '失败')
            info['pauseBtn'].setEnabled(False)
            if not success:
                info['deleteBtn'].setText("移除")
                try:
                    info['deleteBtn'].clicked.disconnect()
                except (RuntimeError, TypeError):
                    pass
                info['deleteBtn'].clicked.connect(
                    lambda: self._removeRow(downloader))
        self.finished.emit(success, bookname)

    def _removeRow(self, downloader):
        info = self.downloaderMap.get(id(downloader))
        if not info:
            return
        if downloader in self.downloaders:
            self.downloaders.remove(downloader)
        removed_row = info['row']
        del self.downloaderMap[id(downloader)]
        self.tableWidget.removeRow(removed_row)
        self._syncRows(removed_row)
        downloader.deleteLater()

    def _downloaderAtRow(self, row):
        for d in self.downloaders:
            info = self.downloaderMap.get(id(d))
            if info and info['row'] == row:
                return d
        return None

    def _onCellDoubleClicked(self, row, column):
        downloader = self._downloaderAtRow(row)
        if not downloader or not downloader._completed:
            return
        self._openFile(downloader)

    def _showContextMenu(self, pos):
        row = self.tableWidget.rowAt(pos.y())
        if row < 0 or row >= self.tableWidget.rowCount():
            return
        downloader = self._downloaderAtRow(row)
        if not downloader or not downloader._completed:
            return

        menu = QMenu(self)
        openAction = menu.addAction("打开文件")
        openAction.triggered.connect(lambda: self._openFile(downloader))
        openDirAction = menu.addAction("打开所在目录")
        openDirAction.triggered.connect(lambda: self._openContainingDir(downloader))
        menu.exec(self.tableWidget.viewport().mapToGlobal(pos))

    def _openFile(self, downloader):
        path = os.path.join(downloader.path, downloader.file_name)
        if not os.path.exists(path):
            QMessageBox.warning(self, "提示", "文件不存在，可能已被移动或删除。")
            return
        try:
            os.startfile(path)
        except Exception as e:
            QMessageBox.warning(self, "提示", f"打开文件失败：{e}")

    def _openContainingDir(self, downloader):
        path = os.path.join(downloader.path, downloader.file_name)
        if not os.path.exists(path):
            QMessageBox.warning(self, "提示", "文件不存在，可能已被移动或删除。")
            return
        try:
            if sys.platform.startswith('win'):
                subprocess.Popen(['explorer', '/select,', path])
            else:
                os.startfile(os.path.dirname(path))
        except Exception as e:
            QMessageBox.warning(self, "提示", f"打开目录失败：{e}")
