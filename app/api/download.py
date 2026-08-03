# coding:utf-8
import requests
import time
from loguru import logger
from .host import get_host
from ..db.account_pool import AccountPool

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


def get_download_url(bookid, hashid, remix_key=None, remix_id=None):
    if remix_key is None or remix_id is None:
        pool = AccountPool()
        account = pool.get_one()
        if account is None:
            return {'status': -1, 'error': 'No available account'}
        remix_id = account['remix_id']
        remix_key = account['remix_key']

    host = get_host()
    url = f'https://{host}/eapi/book/{bookid}/{hashid}/file'

    cookies = {
        "remix_userid": str(remix_id),
        "remix_userkey": remix_key,
    }
    headers = {**ANDROID_HEADERS, 'host': host}

    start = time.time()
    resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
    try:
        data = resp.json().get('file', {})
        allow = data.get('allowDownload', False)
        elapsed = time.time() - start
        if allow:
            logger.success(f"Got download URL in {elapsed:.2f}s")
            return {'status': 1, 'durl': data['downloadLink'], 'remix_id': remix_id}
        else:
            logger.warning(f"Download not allowed, {elapsed:.2f}s")
            return {'status': 0, 'remix_id': remix_id}
    except Exception as e:
        logger.error(f"Get download URL failed: {e}")
        return {'status': -1, 'remix_id': remix_id}
    finally:
        resp.close()


def get_user_profile(remix_id, remix_key):
    host = get_host()
    url = f'https://{host}/eapi/user/profile'

    cookies = {
        "remix_userid": str(remix_id),
        "remix_userkey": remix_key,
    }
    headers = {**ANDROID_HEADERS, 'host': host}

    try:
        resp = requests.get(url, cookies=cookies, headers=headers, timeout=10)
        data = resp.json()
        logger.debug(f"Profile response: {data}")
        user = data.get('user', {})
        downloads_today = user.get('downloads_today', 0)
        downloads_limit = user.get('downloads_limit', 0)
        resp.close()
        return downloads_limit, downloads_today
    except Exception as e:
        logger.error(f"Get profile failed for {remix_id}: {e}")
        return None, None
