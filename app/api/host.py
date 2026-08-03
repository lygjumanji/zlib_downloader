# coding:utf-8
import requests
from loguru import logger
from ..common.config import cfg

_resolved_host = None


def get_host():
    global _resolved_host
    host = cfg.host
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


def _resolve_host(host):
    try:
        resp = requests.head(
            f'https://{host}',
            headers={'user-agent': 'okhttp/3.12.13'},
            allow_redirects=True,
            timeout=10
        )
        from urllib.parse import urlparse
        real_host = urlparse(resp.url).hostname
        resp.close()
        return real_host or host
    except Exception as e:
        logger.warning(f"Failed to resolve host {host}: {e}")
        return host
