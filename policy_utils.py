import json
import ipaddress
from models import AccessPolicy

def is_ip_in_range(ip, ip_range):
    """校验IP是否在白名单内"""
    try:
        return ipaddress.ip_address(ip) in ipaddress.ip_network(ip_range, strict=False)
    except Exception as e:
        print(f"IP校验失败：{e}")
        return False

def match_abac_policy(device_attrs):
    """ABAC策略匹配逻辑（最终修复版）"""
    # 获取默认策略（移除is_active查询，因为模型刚添加该字段，旧数据库无数据）
    policy = AccessPolicy.query.filter_by(policy_name="默认设备策略").first()
    if not policy:
        print("未找到默认设备策略")
        return False, {}

    # 解析策略条件和权限
    conditions = json.loads(policy.conditions)
    permissions = json.loads(policy.permissions)

    # 1. 校验IP段（必须在策略网段内）
    device_ip = device_attrs.get("ip_address")
    policy_ip_range = conditions.get("ip_range")
    if not device_ip or not policy_ip_range:
        print("IP或策略网段为空")
        return False, {}
    if not is_ip_in_range(device_ip, policy_ip_range):
        print(f"IP不匹配：设备IP={device_ip}，策略网段={policy_ip_range}")
        return False, {}

    # 2. 校验OS类型（支持数组多值匹配）
    device_os = device_attrs.get("os_type")
    policy_os = conditions.get("os_type", [])
    # 兼容策略OS是字符串的情况
    if isinstance(policy_os, str):
        policy_os = [policy_os]
    if device_os not in policy_os:
        print(f"OS类型不匹配：设备OS={device_os}，策略允许OS={policy_os}")
        return False, {}

    # 所有条件匹配成功
    print(f"策略匹配成功：设备IP={device_ip}，OS={device_os}")
    return True, permissions