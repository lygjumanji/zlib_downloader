# coding:utf-8
import sys
import os
import re
import time
import uuid
import webbrowser
import requests
from PySide6.QtCore import QThread, Signal, QMutex
from loguru import logger
from ..api.download import get_download_url
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
        self.part_file = ''
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

    def _make_filename(self):
        pattern = cfg.fileNamePattern
        year = self.year if self.year not in ('', '0', 'None') else ''
        name = pattern.replace('%title%', self.raw_title)
        name = name.replace('%year%', year)
        name = name.replace('%author%', self.author)
        name = re.sub(r'[\/\\:*?"<>|]', '', name)
        name = re.sub(r'\s*\(\s*\)', '', name)
        name = name.rstrip(' .')
        if not name.endswith(f'.{self.extension}'):
            name = f"{name}.{self.extension}"
        return name

    def _finish_stopped(self):
        self.status = 'stopped'
        self.sig_status.emit('stopped')
        self.final.emit(False, self.raw_title)

    def run(self):
        self.status = 'downloading'
        self.sig_status.emit('downloading')
        try:
            self.file_name = self._make_filename()
            self.part_file = os.path.join(self.path, f".{self.bookid}.{self.hashid}.part")
            if self._wait_if_paused():
                self._finish_stopped()
                return
            if not self._check_repeat():
                self._log_fail("文件已存在，跳过")
                self.final.emit(False, self.raw_title)
                return
            result = get_download_url(self.bookid, self.hashid)
            if self._wait_if_paused():
                self._cleanup_file()
                self._finish_stopped()
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
            self._cleanup_file()
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
                self.file_name = f"{base}_{uuid.uuid4().hex[:8]}{ext}"
        return True

    def _handle_download(self, durl):
        response = None
        try:
            response = requests.get(durl, stream=True, timeout=30)
            if self._is_stopped():
                self._cleanup_file()
                self._finish_stopped()
                return
            self.sig_start.emit(self.raw_title)
            self._download_file(response)
        except requests.exceptions.ConnectionError:
            self._cleanup_file()
            self._log_fail("连接失败，已打开浏览器")
            webbrowser.open(durl)
            self.final.emit(False, self.raw_title)
        except Exception as e:
            self._cleanup_file()
            logger.error(f"Download error: {e}")
            self._log_fail(str(e))
            self.final.emit(False, self.raw_title)
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass

    def _download_file(self, response):
        file_path = self.part_file
        if not os.path.exists(self.path):
            os.makedirs(self.path, exist_ok=True)
        read = 0
        csize = 1024
        try:
            file_size = int(self.size) if self.size else int(response.headers.get('content-length', 0) or 0)
        except (ValueError, TypeError):
            file_size = 0
        interval_bytes = 0
        interval_start = time.time()

        stopped = False
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=csize):
                if self._is_stopped():
                    stopped = True
                    break
                while self._is_paused():
                    if self._is_stopped():
                        stopped = True
                        break
                    time.sleep(0.1)
                if stopped:
                    break
                if chunk:
                    f.write(chunk)
                    chunk_len = len(chunk)
                    read += chunk_len
                    interval_bytes += chunk_len
                    process = int(read / file_size * 100) if file_size > 0 else 0
                    process = min(process, 100)
                    current_time = time.time()
                    elapsed = current_time - interval_start
                    if elapsed >= 1.0:
                        speed_val = interval_bytes / 1024 / elapsed
                        self.speed.emit(round(speed_val, 2))
                        interval_bytes = 0
                        interval_start = current_time
                    self.sig_down_process.emit(process)

        if stopped or self._is_stopped():
            self._cleanup_file()
            self._finish_stopped()
            return

        elapsed = time.time() - interval_start
        if interval_bytes and elapsed >= 0.05:
            speed_val = interval_bytes / 1024 / elapsed
            self.speed.emit(round(speed_val, 2))

        self._finalize_file(file_path)
        self._completed = True
        self.status = 'completed'
        self.sig_status.emit('completed')
        self._log_download()
        self.final.emit(True, self.raw_title)

    def _finalize_file(self, part_path):
        final_path = os.path.join(self.path, self.file_name)
        if os.path.exists(final_path):
            base, ext = os.path.splitext(self.file_name)
            self.file_name = f"{base}_{uuid.uuid4().hex[:8]}{ext}"
            final_path = os.path.join(self.path, self.file_name)
        try:
            os.replace(part_path, final_path)
        except OSError as e:
            logger.error(f"Failed to finalize file: {e}")
            raise

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
        if self.part_file and os.path.exists(self.part_file):
            try:
                os.remove(self.part_file)
                logger.info(f"Removed incomplete file: {self.part_file}")
            except Exception as e:
                logger.error(f"Failed to remove file: {e}")
