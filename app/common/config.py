# coding:utf-8
import sys
import json
import os
import datetime

YEAR = datetime.datetime.now().year
VERSION = "1.0.0"

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

CONFIG_DIR = os.path.join(BASE_DIR, 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

DEFAULT_CONFIG = {
    "downloadFolder": "download",
    "skipRepeatFiles": True,
    "searchNums": 50,
    "language": 0,
    "searchMode": 0,
    "extensions": 0,
    "accurate": False,
    "host": "zlib.re",
    "fileNamePattern": "%title%(%year%)",
    "maxDownloadThreads": 10,
}

Languages = {
    '中文': 'chinese', '繁体': 'traditional chinese', '英语': 'english',
    '俄语': 'russian', '德语': 'german', '西班牙语': 'spanish',
    '荷兰语': 'dutch', '法语': 'french', '意大利语': 'italian',
    '葡萄牙语': 'portuguese', '巴西葡萄牙语': 'brazilian', '波兰语': 'polish',
    '乌克兰语': 'ukrainian', '保加利亚语': 'bulgarian', '希腊语': 'greek',
    '罗马尼亚语': 'romanian', '土耳其语': 'turkish', '波斯语': 'persian',
    '阿拉伯语': 'arabic', '日语': 'japanese', '瑞典语': 'swedish',
    '匈牙利语': 'hungarian', '塞尔维亚语': 'serbian', '拉丁语': 'latin',
    '克罗地亚语': 'croatian', '捷克语': 'czech', '哈萨克语': 'kazakh',
    '白俄罗斯语': 'belarusian', '印度尼西亚语': 'indonesian',
    '马来西亚语': 'malaysian', '立陶宛语': 'lithuanian',
    '加泰罗尼亚语': 'catalan', '芬兰语': 'finnish', '韩语': 'korean',
    '孟加拉语': 'bengali', '印地语': 'hindi', '丹麦语': 'danish',
    '挪威语': 'norwegian', '越南语': 'vietnamese', '蒙古语': 'mongolian',
    '泰语': 'thai', '希伯来语': 'hebrew', '斯洛文尼亚语': 'slovenian',
    '爱沙尼亚语': 'estonian', '泰米尔语': 'tamil', '泰卢固语': 'telugu',
}

SearchMode = {
    '默认': None, '热度': 'popular', '匹配度': 'bestmatch',
    '名称': 'title', '上传日期': 'date', '出版日期': 'year'
}

Extensions = {
    '所有': None, 'txt': 'txt', 'pdf': 'pdf', 'epub': 'epub',
    'mobi': 'mobi', 'azw': 'azw', 'azw3': 'azw3'
}

FileNameTemplates = [
    ('标题(年份)', '%title%(%year%)'),
    ('标题 - 作者', '%title% - %author%'),
    ('作者 - 标题', '%author% - %title%'),
    ('标题_年份', '%title%_%year%'),
    ('年份.标题', '%year%.%title%'),
    ('年份 - 标题', '%year% - %title%'),
]


class Config:
    def __init__(self):
        self._data = dict(DEFAULT_CONFIG)
        self._load()
        if not os.path.exists(CONFIG_FILE):
            self.save()

    def _load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                saved.pop('repeatFiles', None)
                self._data.update(saved)
            except Exception:
                pass

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    @property
    def downloadFolder(self):
        return self._data['downloadFolder']

    @property
    def skipRepeatFiles(self):
        return self._data['skipRepeatFiles']

    @property
    def searchNums(self):
        return self._data['searchNums']

    @property
    def language(self):
        return self._data['language']

    @property
    def searchMode(self):
        return self._data['searchMode']

    @property
    def extensions(self):
        return self._data['extensions']

    @property
    def accurate(self):
        return self._data['accurate']

    @property
    def host(self):
        return self._data['host']

    @property
    def fileNamePattern(self):
        return self._data['fileNamePattern']

    @property
    def maxDownloadThreads(self):
        return self._data['maxDownloadThreads']


cfg = Config()
