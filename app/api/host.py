# coding:utf-8
import threading
import requests
from loguru import logger
from urllib.parse import urlparse
from ..common.config import cfg

_resolved_host = None
_resolve_lock = threading.Lock()


def get_host():
    global _resolved_host
    host = cfg.host
    with _resolve_lock:
        if _resolved_host and _resolved_host != host:
            _resolved_host = None
        if _resolved_host:
            return _resolved_host
        resolved = _resolve_host(host)
        if resolved and resolved != host:
            _resolved_host = resolved
            logger.info(f"Host resolved: {host} -> {resolved}")
            return resolved
        _resolved_host = host
        return host


def _reset_resolved_host():
    global _resolved_host
    _resolved_host = None


def _resolve_host(host):
    resp = None
    try:
        resp = requests.head(
            f'https://{host}',
            headers={'user-agent': 'okhttp/3.12.13'},
            allow_redirects=True,
            timeout=10
        )
        real_host = urlparse(resp.url).hostname
        return real_host or host
    except Exception as e:
        logger.warning(f"Failed to resolve host {host}: {e}")
        return host
    finally:
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass
