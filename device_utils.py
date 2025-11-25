import hashlib
import uuid
from flask import request

def get_client_ip():
    """获取客户端IP（支持真机接入）"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]
    return request.environ.get('REMOTE_ADDR')

def generate_device_fingerprint(device_model):
    """生成设备唯一指纹"""
    ip = get_client_ip()
    # 浏览器信息（Web场景，真机可扩展SDK采集）
    user_agent = request.headers.get('User-Agent', 'unknown')
    raw_data = f"{device_model}_{ip}_{user_agent}_{uuid.uuid4()}"
    return hashlib.sha256(raw_data.encode()).hexdigest()[:64]

def collect_device_attrs(device_model):
    """采集设备属性"""
    return {
        "device_fingerprint": generate_device_fingerprint(device_model),
        "device_model": device_model,
        "ip_address": get_client_ip(),
        "os_type": "Windows" if "Windows" in request.headers.get('User-Agent', '') else "Other"
    }