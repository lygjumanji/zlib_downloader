# coding:utf-8
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QCheckBox, QMenu, QLabel, QProgressBar, QMessageBox
)
from ..tools.searcher import Searcher
from ..common.config import cfg, YEAR, Languages, SearchMode, Extensions


class SearchPage(QWidget):
    sig_download_start = Signal(list)

    def __init__(self):
        super().__init__()
        self.books = None
        self.searchEngine = None
        self.add_cb = False
        self._searchSeq = 0
        self._searchEngines = set()
        self._currentPagination = None
        self._initUI()
        self._bind()

    def _initUI(self):
        layout = QVBoxLayout(self)

        searchLayout = QHBoxLayout()
        self.searchLineEdit = QLineEdit()
        self.searchLineEdit.setPlaceholderText("请输入书名进行搜索")
        self.searchLineEdit.setMinimumWidth(300)
        self.searchBtn = QPushButton("搜索")
        self.searchBtn.clicked.connect(self.search)
        searchLayout.addWidget(self.searchLineEdit, 1)
        searchLayout.addWidget(self.searchBtn)

        self.accurate_CheckBox = QCheckBox("精准搜索")

        hbox = QHBoxLayout()
        self.langComboBox = QComboBox()
        for k in Languages:
            self.langComboBox.addItem(k)

        self.searchComboBox = QComboBox()
        for k in SearchMode:
            self.searchComboBox.addItem(k)

        self.extComboBox = QComboBox()
        for k in Extensions:
            self.extComboBox.addItem(k)

        self.yearFromComboBox = QComboBox()
        self.yearToComboBox = QComboBox()
        for combo in (self.yearFromComboBox, self.yearToComboBox):
            combo.addItem("不限")
            for y in range(YEAR, 1899, -1):
                combo.addItem(str(y))

        hbox.addWidget(self.accurate_CheckBox)
        hbox.addWidget(QLabel("排序:"))
        hbox.addWidget(self.searchComboBox)
        hbox.addWidget(QLabel("语言:"))
        hbox.addWidget(self.langComboBox)
        hbox.addWidget(QLabel("格式:"))
        hbox.addWidget(self.extComboBox)
        hbox.addWidget(QLabel("年份:"))
        hbox.addWidget(self.yearFromComboBox)
        hbox.addWidget(QLabel("至"))
        hbox.addWidget(self.yearToComboBox)
        hbox.addStretch()

        self.tableWidget = QTableWidget()
        self.tableWidget.setSortingEnabled(True)
        self.tableWidget.setColumnCount(7)
        self.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tableWidget.verticalHeader().hide()
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.tableWidget.setHorizontalHeaderLabels(
            ['书名', '年份', '作者', '大小', '格式', '出版社', '页数'])
        self.tableWidget.verticalHeader().setDefaultSectionSize(36)
        self.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self._showContextMenu)
        self._colRatios = [240, 50, 120, 60, 45, 100, 45]

        self.statusBar = QLabel("欢迎使用 Zlib Downloader")
        self.statusBar.setAlignment(Qt.AlignCenter)

        self.navWidget = QWidget()
        self.navLayout = QHBoxLayout(self.navWidget)
        self.navLayout.setContentsMargins(0, 0, 0, 0)
        self.preBtn = QPushButton("上一页")
        self.preBtn.clicked.connect(self._prePage)
        self.nextBtn = QPushButton("下一页")
        self.nextBtn.clicked.connect(self._nextPage)
        self.navLayout.addWidget(self.preBtn)
        self.navLayout.addWidget(self.statusBar, 1)
        self.navLayout.addWidget(self.nextBtn)
        self.navWidget.hide()

        self._initComboBox()

        layout.addLayout(searchLayout)
        layout.addLayout(hbox)
        layout.addWidget(self.tableWidget)
        layout.addWidget(self.navWidget)

    def _bind(self):
        self.searchLineEdit.returnPressed.connect(self.search)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        total = sum(self._colRatios)
        tableWidth = self.tableWidget.viewport().width()
        for i, ratio in enumerate(self._colRatios):
            self.tableWidget.setColumnWidth(i, int(tableWidth * ratio / total))

    def _initComboBox(self):
        self.searchComboBox.setCurrentIndex(cfg.searchMode)
        self.extComboBox.setCurrentIndex(cfg.extensions)
        self.langComboBox.setCurrentIndex(cfg.language)
        self.accurate_CheckBox.setChecked(cfg.accurate)

    def _saveParams(self):
        cfg.set("language", self.langComboBox.currentIndex())
        cfg.set("extensions", self.extComboBox.currentIndex())
        cfg.set("searchMode", self.searchComboBox.currentIndex())
        cfg.set("accurate", self.accurate_CheckBox.isChecked())

    def _yearValue(self, combo):
        text = combo.currentText()
        return text if text != "不限" else ""

    def _nextPage(self):
        nxt = self._currentPagination.get('next') if self._currentPagination else None
        if nxt:
            self.search(nxt)

    def _prePage(self):
        pre = self._currentPagination.get('before') if self._currentPagination else None
        if pre:
            self.search(pre)

    def _updateStatusBar(self):
        if not self._currentPagination:
            return
        current = self._currentPagination.get('current', 0)
        total = self._currentPagination.get('total_pages', 0)
        self.statusBar.setText(f"[{current}/{total}]")

    def search(self, page=None):
        title = self.searchLineEdit.text()
        if not title:
            QMessageBox.warning(self, "提示", "请输入书名")
            return

        self._saveParams()
        self.tableWidget.clearContents()
        self.navWidget.show()

        lang = Languages[self.langComboBox.currentText()]
        ext = Extensions[self.extComboBox.currentText()]
        mode = SearchMode[self.searchComboBox.currentText()]
        accurate = "1" if self.accurate_CheckBox.isChecked() else None
        yearFrom = self._yearValue(self.yearFromComboBox) or None
        yearTo = self._yearValue(self.yearToComboBox) or None
        n = cfg.searchNums

        self._searchSeq += 1
        seq = self._searchSeq
        engine = Searcher(
            title, languages=lang, extensions=ext, page=page,
            order=mode, limit=str(n), e=accurate,
            yearFrom=yearFrom, yearTo=yearTo
        )
        self._searchEngines.add(engine)
        engine.sig_success.connect(lambda books, s=seq: self._showBooks(books, s))
        engine.sig_fail.connect(lambda code, s=seq: self._onFailed(code, s))
        engine.finished.connect(lambda e=engine: self._searchEngineFinished(e))
        self.searchEngine = engine
        self.statusBar.setText(f"搜索中: {title} ...")
        engine.start()

    def _searchEngineFinished(self, engine):
        self._searchEngines.discard(engine)
        engine.deleteLater()
        if engine is self.searchEngine:
            self.searchEngine = None

    def _showBooks(self, books, seq):
        if seq != self._searchSeq:
            return
        self.books = books
        if self.searchEngine and self.searchEngine.pagination:
            self._currentPagination = self.searchEngine.pagination
        self._updateStatusBar()
        self._fillTable(books)

    def _fillTable(self, books):
        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.setRowCount(len(books))
        for i, book in enumerate(books):
            year = str(book.get('year', ''))
            if year == '0' or year == 'None':
                year = ''

            item0 = QTableWidgetItem(book.get('title', ''))
            item0.setData(Qt.UserRole, i)
            item0.setToolTip(book.get('title', ''))
            item0.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.tableWidget.setItem(i, 0, item0)

            item1 = QTableWidgetItem(year)
            item1.setTextAlignment(Qt.AlignCenter)
            self.tableWidget.setItem(i, 1, item1)

            author = book.get('author', '')
            item2 = QTableWidgetItem(author)
            item2.setToolTip(author)
            item2.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.tableWidget.setItem(i, 2, item2)

            item3 = QTableWidgetItem(book.get('filesizeString', ''))
            item3.setTextAlignment(Qt.AlignCenter)
            self.tableWidget.setItem(i, 3, item3)

            item4 = QTableWidgetItem(book.get('extension', ''))
            item4.setTextAlignment(Qt.AlignCenter)
            self.tableWidget.setItem(i, 4, item4)

            publisher = book.get('publisher', '') or ''
            item5 = QTableWidgetItem(publisher)
            item5.setToolTip(publisher)
            item5.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.tableWidget.setItem(i, 5, item5)

            pages = str(book.get('pages', '') or '')
            item6 = QTableWidgetItem(pages)
            item6.setTextAlignment(Qt.AlignCenter)
            self.tableWidget.setItem(i, 6, item6)
        self.tableWidget.setSortingEnabled(True)

    def _onFailed(self, code, seq):
        if seq != self._searchSeq:
            return
        self.tableWidget.clearContents()
        messages = {
            0: ("结果为空", "请更改搜索条件"),
            -1: ("未知异常", "请稍后重试"),
            -999: ("搜索词异常", "请修改搜索词"),
            999: ("请求限制", "搜索过于频繁，请稍后再试"),
        }
        title, content = messages.get(code, ("错误", "未知错误"))
        QMessageBox.warning(self, title, content)

    def _showContextMenu(self, pos):
        if not self.books:
            return
        row = self.tableWidget.rowAt(pos.y())
        if row < 0 or row >= self.tableWidget.rowCount():
            return

        item = self.tableWidget.item(row, 0)
        if not item:
            return
        source_row = item.data(Qt.UserRole)
        if source_row is None or source_row < 0 or source_row >= len(self.books):
            return

        menu = QMenu(self)
        downloadAction = menu.addAction("下载书籍")
        downloadAction.triggered.connect(lambda: self._download(source_row))
        menu.addSeparator()
        detailAction = menu.addAction("书籍详情")
        detailAction.triggered.connect(lambda: self._showBookDetail(source_row))
        menu.exec(self.tableWidget.viewport().mapToGlobal(pos))

    def _download(self, row):
        if row >= len(self.books):
            return
        book = self.books[row]
        self.sig_download_start.emit([
            book.get('id'),
            book.get('hash'),
            book.get('title'),
            book.get('extension'),
            book.get('filesize'),
            book.get('year', ''),
            book.get('author', '')
        ])

    def _showBookDetail(self, row):
        if row >= len(self.books):
            return
        book = self.books[row]
        from .book_detail_dialog import BookDetailDialog
        dialog = BookDetailDialog(book, self)
        dialog.exec()
