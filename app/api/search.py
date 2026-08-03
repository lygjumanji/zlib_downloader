# coding:utf-8
import requests
import time
from loguru import logger
from .host import get_host

ANDROID_HEADERS = {
    'source': 'android',
    'android-app-language': 'zh',
    'android-app-version': '1.11.4',
    'appversion': '1.11.4',
    'android-os-version': '7.1.2',
    'android-mobile-version': 'SM-G9810',
    'content-type': 'application/x-www-form-urlencoded',
    'user-agent': 'okhttp/3.12.13',
}


def search_books(bookname, languages=None, page=None, extensions=None,
                 order=None, limit="20", e=None, yearFrom=None, yearTo=None):
    host = get_host()
    url = f'https://{host}/eapi/book/search'

    headers = {**ANDROID_HEADERS, 'host': host}

    data = {
        'message': bookname,
        'languages[]': languages or ["Chinese"],
        'extensions[]': extensions,
        'order': order,
        'limit': limit,
        'e': e,
        'page': page,
        'yearFrom': yearFrom,
        'yearTo': yearTo
    }

    start = time.time()
    resp = requests.post(url, headers=headers, data=data, timeout=(5, 15))
    try:
        result = resp.json()
        elapsed = time.time() - start
        logger.success(f"Search '{bookname}' OK, {elapsed:.2f}s")
        return result
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return None
    finally:
        resp.close()
