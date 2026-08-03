# coding:utf-8
import sys
import os
import re
import time
import webbrowser
import requests
from PySide6.QtCore import QThread, Signal, QMutex
from loguru import logger
from ..api.download import get_download_url
from ..db.account_pool import AccountPool
from ..common.config import cfg

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'download.log')
FAIL_LOG_FILE = os.path.join(LOG_DIR, 'download_fail.log')


class Downloader(QThread):
    sig_down_process = Signal(int)
    sig_rate_limit = Signal(int)
    speed = Signal(float)
    final = Signal(bool, str)
    sig_start = Signal(str)
    sig_status = Signal(str)

    def __init__(self, bookid, hashid, bookname, extension, size=None, year='', author=''):
        super().__init__()
        self.bookid = bookid
        self.hashid = hashid
        self.raw_title = bookname
        self.extension = extension
        self.path = cfg.downloadFolder
        self.size = size
        self.year = str(year) if year else ''
        self.author = str(author) if author else ''
        self._paused = False
        self._stopped = False
        self._completed = False
        self._mutex = QMutex()
        self.file_name = ''
        self.status = 'pending'

    def pause(self):
        self._mutex.lock()
        self._paused = True
        self.status = 'paused'
        self._mutex.unlock()
        self.sig_status.emit('paused')

    def resume(self):
        self._mutex.lock()
        self._paused = False
        self.status = 'downloading'
        self._mutex.unlock()
        self.sig_status.emit('downloading')

    def stop(self):
        self._mutex.lock()
        self._stopped = True
        self._paused = False
        self._mutex.unlock()

    def _is_stopped(self):
        self._mutex.lock()
        v = self._stopped
        self._mutex.unlock()
        return v

    def _is_paused(self):
        self._mutex.lock()
        v = self._paused
        self._mutex.unlock()
        return v

    def _wait_if_paused(self):
        while True:
            if self._is_stopped():
                return True
            if not self._is_paused():
                return False
            time.sleep(0.1)
        return False

    def _make_filename(self):
        pattern = cfg.fileNamePattern
        name = pattern.replace('%title%', self.raw_title)
        name = name.replace('%year%', self.year)
        name = name.replace('%author%', self.author)
        name = re.sub(r'[\/\\:*?"<>|]', '', name)
        if not name.endswith(f'.{self.extension}'):
            name = f"{name}.{self.extension}"
        return name

    def run(self):
        self.status = 'downloading'
        self.sig_status.emit('downloading')
        try:
            self.file_name = self._make_filename()
            if self._wait_if_paused():
                self.status = 'stopped'
                self.sig_status.emit('stopped')
                self.final.emit(False, self.raw_title)
                return
            if not self._check_repeat():
                self._log_fail("文件已存在，跳过")
                self.final.emit(False, self.raw_title)
                return
            result = get_download_url(self.bookid, self.hashid)
            remix_id = result.get('remix_id')
            if remix_id:
                pool = AccountPool()
                pool.decrement_num(remix_id)
            if self._wait_if_paused():
                self._cleanup_file()
                self.status = 'stopped'
                self.sig_status.emit('stopped')
                self.final.emit(False, self.raw_title)
                return
            status_code = result.get('status', -1)
            if status_code == 1:
                self._handle_download(result['durl'])
            elif status_code == 0:
                self._log_fail("下载权限不足")
                self.final.emit(False, self.raw_title)
            else:
                self._log_fail("请求限制(频率过高)")
                self.sig_rate_limit.emit(999)
        except Exception as e:
            logger.error(f"Download error: {e}")
            self._log_fail(str(e))
            self.final.emit(False, self.raw_title)

    def _check_repeat(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path, exist_ok=True)
        file_path = os.path.join(self.path, self.file_name)
        if os.path.exists(file_path):
            if cfg.skipRepeatFiles:
                logger.info(f"File exists, skipping: {self.file_name}")
                return False
            else:
                base, ext = os.path.splitext(self.file_name)
                self.file_name = f"{base}_{int(time.time())}{ext}"
        return True

    def _handle_download(self, durl):
        try:
            response = requests.get(durl, stream=True, timeout=30)
            if self._is_stopped():
                response.close()
                self._cleanup_file()
                self.status = 'stopped'
                self.sig_status.emit('stopped')
                self.final.emit(False, self.raw_title)
                return
            self.sig_start.emit(self.raw_title)
            self._download_file(response)
        except requests.exceptions.ConnectionError:
            self._log_fail("连接失败，已打开浏览器")
            webbrowser.open(durl)
            self.final.emit(False, self.raw_title)
        except Exception as e:
            logger.error(f"Download error: {e}")
            self._log_fail(str(e))
            self.final.emit(False, self.raw_title)

    def _download_file(self, response):
        file_path = os.path.join(self.path, self.file_name)
        read = 0
        csize = 1024
        file_size = int(self.size) if self.size else int(response.headers.get('content-length', 1))
        interval_bytes = 0
        interval_start = time.time()

        with open(file_path, 'ab') as f:
            for chunk in response.iter_content(chunk_size=csize):
                if self._is_stopped():
                    response.close()
                    f.close()
                    self._cleanup_file()
                    self.status = 'stopped'
                    self.sig_status.emit('stopped')
                    self.final.emit(False, self.raw_title)
                    return
                while self._is_paused():
                    if self._is_stopped():
                        response.close()
                        f.close()
                        self._cleanup_file()
                        self.status = 'stopped'
                        self.sig_status.emit('stopped')
                        self.final.emit(False, self.raw_title)
                        return
                    time.sleep(0.1)
                if chunk:
                    f.write(chunk)
                    chunk_len = len(chunk)
                    read += chunk_len
                    interval_bytes += chunk_len
                    read = min(read, file_size)
                    process = int(read / file_size * 100) if file_size > 0 else 0
                    current_time = time.time()
                    elapsed = current_time - interval_start
                    if elapsed >= 1.0:
                        speed_val = interval_bytes / 1024 / elapsed
                        self.speed.emit(round(speed_val, 2))
                        interval_bytes = 0
                        interval_start = current_time
                    self.sig_down_process.emit(process)

        self._completed = True
        self.status = 'completed'
        self.sig_status.emit('completed')
        self._log_download()
        self.final.emit(True, self.raw_title)

    def _log_download(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        file_path = os.path.join(self.path, self.file_name)
        log_line = f"[{timestamp}] {self.raw_title} | {file_path}\n"
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line)
        logger.info(f"Download logged: {self.raw_title}")

    def _log_fail(self, reason):
        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {self.raw_title} | 失败原因: {reason}\n"
        with open(FAIL_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line)
        logger.warning(f"Download failed: {self.raw_title} - {reason}")

    def _cleanup_file(self):
        if self._completed:
            return
        file_path = os.path.join(self.path, self.file_name)
        if self.file_name and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Removed incomplete file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to remove file: {e}")
