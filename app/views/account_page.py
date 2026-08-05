# coding:utf-8
import json
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QFileDialog, QDialog, QLineEdit,
    QLabel, QDialogButtonBox, QMessageBox
)
from ..db.account_pool import AccountPool
from ..api.download import get_user_profile
from ..api.auth import login


class LoginWorker(QThread):
    login_done = Signal(str, str)
    login_fail = Signal(str)

    def __init__(self, email, password):
        super().__init__()
        self.email = email
        self.password = password

    def run(self):
        remix_id, remix_key = login(self.email, self.password)
        if remix_id and remix_key:
            self.login_done.emit(remix_id, remix_key)
        else:
            self.login_fail.emit("登录失败，请检查用户名和密码")


class ProfileWorker(QThread):
    profile_done = Signal(list)

    def __init__(self, accounts):
        super().__init__()
        self.accounts = accounts

    def run(self):
        results = []
        for acc in self.accounts:
            limit, today = get_user_profile(acc['remix_id'], acc['remix_key'])
            if limit is not None:
                results.append({
                    'remix_id': acc['remix_id'],
                    'downloads_limit': limit,
                    'downloads_today': today,
                })
        self.profile_done.emit(results)


class AccountPage(QWidget):
    def __init__(self):
        super().__init__()
        self.pool = AccountPool()
        self.worker = None
        self._initUI()
        self._loadAccounts()

    def _initUI(self):
        layout = QVBoxLayout(self)

        hbox = QHBoxLayout()
        self.addBtn = QPushButton("添加账户")
        self.deleteBtn = QPushButton("删除选中")
        self.refreshBtn = QPushButton("刷新列表")
        self.refreshLimitsBtn = QPushButton("刷新额度")
        self.importBtn = QPushButton("导入 JSON")
        self.exportBtn = QPushButton("导出 JSON")

        self.addBtn.clicked.connect(self._addAccount)
        self.deleteBtn.clicked.connect(self._deleteAccount)
        self.refreshBtn.clicked.connect(self._loadAccounts)
        self.refreshLimitsBtn.clicked.connect(self._refreshLimits)
        self.importBtn.clicked.connect(self._importJson)
        self.exportBtn.clicked.connect(self._exportJson)

        hbox.addWidget(self.addBtn)
        hbox.addWidget(self.deleteBtn)
        hbox.addWidget(self.refreshBtn)
        hbox.addWidget(self.importBtn)
        hbox.addWidget(self.exportBtn)
        hbox.addWidget(self.refreshLimitsBtn)
        hbox.addStretch()

        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget.setHorizontalHeaderLabels(
            ['Remix ID', 'Remix Key', '剩余额度', '最大额度', '今日下载'])
        self.tableWidget.verticalHeader().hide()

        layout.addLayout(hbox)
        layout.addWidget(self.tableWidget)

    def _loadAccounts(self):
        accounts = self.pool.get_all()
        self.tableWidget.setRowCount(len(accounts))
        for i, acc in enumerate(accounts):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(str(acc['remix_id'])))
            self.tableWidget.setItem(i, 1, QTableWidgetItem(acc['remix_key']))
            self.tableWidget.setItem(i, 2, QTableWidgetItem(str(acc['num'])))
            self.tableWidget.setItem(i, 3, QTableWidgetItem(str(acc.get('downloads_limit', 0))))
            self.tableWidget.setItem(i, 4, QTableWidgetItem(str(acc.get('downloads_today', 0))))

    def _refreshLimits(self):
        accounts = self.pool.get_all()
        if not accounts:
            QMessageBox.warning(self, "提示", "没有账户可刷新")
            return
        self.refreshLimitsBtn.setEnabled(False)
        self.refreshLimitsBtn.setText("刷新中...")
        self.worker = ProfileWorker(accounts)
        self.worker.profile_done.connect(self._onLimitsRefreshed)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            if not self.worker.wait(3000):
                self.worker.terminate()
                self.worker.wait(1000)

    def _onLimitsRefreshed(self, results):
        for r in results:
            self.pool.update_limits(r['remix_id'], r['downloads_limit'], r['downloads_today'])
        self._loadAccounts()
        self.refreshLimitsBtn.setEnabled(True)
        self.refreshLimitsBtn.setText("刷新额度")
        QMessageBox.information(self, "成功", f"已刷新 {len(results)} 个账户额度")

    def _addAccount(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加账户")
        dialog.setMinimumWidth(320)
        formLayout = QVBoxLayout(dialog)
        self._loginWorker = None

        formLayout.addWidget(QLabel("用户名/邮箱:"))
        emailEdit = QLineEdit()
        emailEdit.setPlaceholderText("请输入 Z-Library 登录邮箱")
        formLayout.addWidget(emailEdit)

        formLayout.addWidget(QLabel("密码:"))
        passwordEdit = QLineEdit()
        passwordEdit.setEchoMode(QLineEdit.Password)
        passwordEdit.setPlaceholderText("请输入登录密码")
        formLayout.addWidget(passwordEdit)

        fetchBtn = QPushButton("自动获取 Remix ID 和 Key")
        formLayout.addWidget(fetchBtn)

        formLayout.addWidget(QLabel("Remix ID:"))
        idEdit = QLineEdit()
        formLayout.addWidget(idEdit)

        formLayout.addWidget(QLabel("Remix Key:"))
        keyEdit = QLineEdit()
        formLayout.addWidget(keyEdit)

        formLayout.addWidget(QLabel("剩余额度 (默认 10):"))
        numEdit = QLineEdit("10")
        formLayout.addWidget(numEdit)

        statusLabel = QLabel("")
        statusLabel.setAlignment(Qt.AlignCenter)
        formLayout.addWidget(statusLabel)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        formLayout.addWidget(buttons)

        def _onLoginDone(remix_id, remix_key):
            idEdit.setText(remix_id)
            keyEdit.setText(remix_key)
            statusLabel.setText("获取成功")
            fetchBtn.setEnabled(True)
            QMessageBox.information(dialog, "成功", "已获取 Remix ID 和 Key")

        def _onLoginFail(msg):
            statusLabel.setText(msg)
            fetchBtn.setEnabled(True)
            QMessageBox.warning(dialog, "失败", msg)

        def _clearLoginWorker(worker):
            if self._loginWorker is worker:
                self._loginWorker = None
            worker.deleteLater()

        def _onFetch():
            email = emailEdit.text().strip()
            password = passwordEdit.text().strip()
            if not email or not password:
                QMessageBox.warning(dialog, "提示", "请输入用户名和密码")
                return
            fetchBtn.setEnabled(False)
            statusLabel.setText("登录获取中...")
            worker = LoginWorker(email, password)
            self._loginWorker = worker
            worker.login_done.connect(_onLoginDone)
            worker.login_fail.connect(_onLoginFail)
            worker.finished.connect(lambda w=worker: _clearLoginWorker(w))
            worker.start()

        def _stopLoginWorker():
            worker = self._loginWorker
            if worker and worker.isRunning():
                if not worker.wait(3000):
                    worker.terminate()
                    worker.wait(1000)
                self._loginWorker = None

        fetchBtn.clicked.connect(_onFetch)
        passwordEdit.returnPressed.connect(fetchBtn.click)
        dialog.finished.connect(_stopLoginWorker)

        if dialog.exec():
            try:
                remix_id = int(idEdit.text().strip())
                remix_key = keyEdit.text().strip()
                num = int(numEdit.text().strip()) if numEdit.text().strip() else 10
                if remix_key:
                    self.pool.add_account(remix_id, remix_key, num)
                    self._loadAccounts()
                    QMessageBox.information(self, "成功", "账户已添加")
                else:
                    QMessageBox.warning(self, "提示", "请输入 Remix Key")
            except ValueError:
                QMessageBox.warning(self, "提示", "Remix ID 必须为数字")

    def _deleteAccount(self):
        row = self.tableWidget.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择要删除的账户")
            return
        remix_id = int(self.tableWidget.item(row, 0).text())
        reply = QMessageBox.question(self, "确认删除", f"确定要删除账户 {remix_id} 吗？")
        if reply == QMessageBox.Yes:
            self.pool.delete_account(remix_id)
            self._loadAccounts()
            QMessageBox.information(self, "成功", "账户已删除")

    def _importJson(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入 JSON", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                for acc in data:
                    self.pool.add_account(
                        acc['remix_id'], acc['remix_key'], acc.get('num', 10),
                        acc.get('downloads_limit', 10), acc.get('downloads_today', 0))
                self._loadAccounts()
                QMessageBox.information(self, "成功", f"导入 {len(data)} 个账户")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导入失败: {e}")

    def _exportJson(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出 JSON", "accounts.json", "JSON Files (*.json)")
        if not path:
            return
        try:
            accounts = self.pool.get_all()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(accounts, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "成功", f"导出 {len(accounts)} 个账户")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出失败: {e}")
