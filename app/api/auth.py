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


def login(email, password):
    host = get_host()
    url = f'https://{host}/eapi/user/login'

    headers = {**ANDROID_HEADERS, 'host': host}
    data = {
        'email': email,
        'password': password,
    }

    start = time.time()
    resp = None
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=(5, 15))
        result = resp.json()
        logger.debug(f"Login response: {result}")
        user = result.get('user') or {}
        remix_id = user.get('id')
        remix_key = user.get('remix_userkey')

        if not remix_id or not remix_key:
            cookies = resp.cookies.get_dict()
            remix_id = remix_id or cookies.get('remix_userid')
            remix_key = remix_key or cookies.get('remix_userkey')

        if not remix_id or not remix_key:
            logger.warning(f"Login failed, no remix in response, {time.time() - start:.2f}s")
            return None, None

        logger.success(f"Login OK, {time.time() - start:.2f}s")
        return str(remix_id), remix_key
    except Exception as e:
        logger.error(f"Login error: {e}")
        return None, None
    finally:
        if resp is not None:
            resp.close()
