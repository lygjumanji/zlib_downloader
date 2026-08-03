# coding:utf-8
import psutil
import uuid


def get_first_mac():
    interfaces = psutil.net_if_addrs()
    for interface, addrs in interfaces.items():
        for addr in addrs:
            if addr.family == psutil.AF_LINK:
                return addr.address
    return "00:00:00:00:00:00"


def get_uuid():
    mac = get_first_mac()
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, mac))
