import hashlib
import uuid
from flask import request

def get_client_ip():
    """获取客户端真实IP（支持真机/代理/内网接入）"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        ip = request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif request.remote_addr:
        ip = request.remote_addr
    else:
        ip = '127.0.0.1'
    return ip

def get_os_type(user_agent, device_model):
    """双重保障OS识别（UA+设备型号，避免误判）"""
    user_agent = user_agent.lower()
    device_model = device_model.lower()

    # 优先通过设备型号判断（用户输入的型号更准确）
    if 'windows 11' in device_model:
        return 'Windows 11'
    elif 'windows' in device_model:
        return 'Windows'
    elif 'android' in device_model:
        return 'Android'
    elif 'ios' in device_model or 'iphone' in device_model or 'ipad' in device_model:
        return 'iOS'

    # 设备型号未明确时，用UA辅助判断
    if 'windows' in user_agent:
        return 'Windows 11' if 'windows nt 10.0' in user_agent else 'Windows'
    elif 'android' in user_agent:
        return 'Android'
    elif 'ios' in user_agent:
        return 'iOS'
    else:
        return 'Other'

def generate_device_fingerprint(device_model):
    """生成设备唯一指纹"""
    ip = get_client_ip()
    user_agent = request.user_agent.string if request.user_agent else request.headers.get('User-Agent', 'unknown')
    raw_data = f"{device_model}_{ip}_{user_agent}_{uuid.uuid4()}"
    return hashlib.sha256(raw_data.encode()).hexdigest()[:64]

def collect_device_attrs(device_model):
    """采集设备核心属性（传入device_model给OS识别函数）"""
    user_agent = request.user_agent.string if request.user_agent else request.headers.get('User-Agent', 'unknown')
    return {
        "device_fingerprint": generate_device_fingerprint(device_model),
        "device_model": device_model,
        "ip_address": get_client_ip(),
        "os_type": get_os_type(user_agent, device_model)  # 传入两个参数：UA+设备型号
    }