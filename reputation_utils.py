import threading
import time
from datetime import datetime
from models import db, Device, OperationLog

REPUTATION_THRESHOLD = 60  # 信誉值阈值
CALCULATE_INTERVAL = 30  # 计算周期（秒）


def calculate_device_reputation(app):
    """定时计算所有设备信誉值（修复关联错误）"""
    while True:
        # 使用传入的 app 实例创建上下文
        with app.app_context():
            try:
                print("Calculating device reputation...")
                devices = Device.query.all()
                print(f"Found {len(devices)} devices")

                for device in devices:
                    # 关键修复1：OperationLog 关联的是 device_fingerprint（不是 device_id）
                    # 原错误：OperationLog.device_id == device.device_fingerprint（字段名不匹配）
                    logs = OperationLog.query.filter(
                        OperationLog.device_fingerprint == device.device_fingerprint,  # 字段名统一
                        OperationLog.create_time > device.last_calc_time
                    ).all()

                    # 计算总评分（合法操作+10，非法操作-50）
                    total_score = sum(log.score for log in logs) if logs else 0
                    # 关键修复2：限制信誉值最大值为100（避免超过初始分）
                    new_reputation = max(0, min(100, device.current_reputation + total_score))

                    # 更新设备信誉值与计算时间
                    device.current_reputation = new_reputation
                    device.last_calc_time = datetime.utcnow()
                    print(f"设备 {device.device_fingerprint}：原信誉值={device.current_reputation}，变化分={total_score}，新信誉值={new_reputation}")  # 新增日志，方便调试

                    # 信誉值低于阈值：清空该设备所有操作日志
                    if new_reputation < REPUTATION_THRESHOLD:
                        OperationLog.query.filter(
                            OperationLog.device_fingerprint == device.device_fingerprint  # 字段名统一
                        ).delete()
                        print(f"设备 {device.device_fingerprint} 信誉值低于阈值（{REPUTATION_THRESHOLD}），已清空日志")

                db.session.commit()
                print(f"Reputation calculation completed at {datetime.utcnow()}\n")

            except Exception as e:
                print(f"信誉值计算错误：{str(e)}")
                db.session.rollback()

        time.sleep(CALCULATE_INTERVAL)


def start_reputation_calculator(app):
    """启动信誉值计算线程"""
    calculator_thread = threading.Thread(
        target=calculate_device_reputation,
        args=(app,),  # 传递 app 实例
        daemon=True,
        name="calculate_device_reputation"
    )
    calculator_thread.start()
    print("Reputation calculator thread started\n")