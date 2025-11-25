import json
import ipaddress
from models import AccessPolicy


def is_ip_in_range(ip, ip_range):
    """校验IP是否在白名单内"""
    try:
        return ipaddress.ip_address(ip) in ipaddress.ip_network(ip_range)
    except:
        return False


def match_abac_policy(device_attrs):
    """ABAC策略匹配逻辑"""
    # 获取默认策略
    policy = AccessPolicy.query.filter_by(policy_name="默认设备策略").first()
    if not policy:
        return False, {}

    conditions = json.loads(policy.conditions)
    permissions = json.loads(policy.permissions)

    # 校验IP段
    if not is_ip_in_range(device_attrs["ip_address"], conditions["ip_range"]):
        return False, permissions
    # 校验设备类型
    if device_attrs["os_type"] != conditions["os_type"]:
        return False, permissions

    return True, permissions  # 匹配成功，返回权限