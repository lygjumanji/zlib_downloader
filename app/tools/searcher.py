# coding:utf-8
from PySide6.QtCore import QThread, Signal
from loguru import logger
from ..api.search import search_books


class Searcher(QThread):
    sig_success = Signal(list)
    sig_fail = Signal(int)

    def __init__(self, bookname, languages=None, extensions=None, page=None,
                 order="bestmatch", limit="100", e=None, yearFrom=None, yearTo=None):
        super().__init__()
        self.bookname = bookname
        self.languages = languages
        self.extensions = extensions
        self.page = page
        self.order = order
        self.limit = limit
        self.e = e
        self.yearFrom = yearFrom
        self.yearTo = yearTo
        self.pagination = None

    def run(self):
        try:
            result = search_books(
                self.bookname,
                languages=self.languages,
                page=self.page,
                extensions=self.extensions,
                order=self.order,
                limit=self.limit,
                e=self.e,
                yearFrom=self.yearFrom,
                yearTo=self.yearTo
            )
            if result is None:
                self.sig_fail.emit(-1)
                return
            if result.get('success') == 1:
                books = result.get('books', [])
                if books:
                    self.pagination = result.get('pagination')
                    self.sig_success.emit(books)
                else:
                    self.sig_fail.emit(0)
            else:
                self.sig_fail.emit(-1)
        except Exception as e:
            logger.error(f"Search error: {e}")
            self.sig_fail.emit(-999)
