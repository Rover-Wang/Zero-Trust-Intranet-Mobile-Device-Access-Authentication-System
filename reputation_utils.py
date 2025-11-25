import threading
import time
from datetime import datetime
from models import db, Device, OperationLog

REPUTATION_THRESHOLD = 60  # 信誉值阈值
CALCULATE_INTERVAL = 30  # 计算周期（秒）


def calculate_device_reputation(app):
    """定时计算所有设备信誉值"""
    while True:
        # 使用传入的 app 实例创建上下文
        with app.app_context():
            try:
                print("Calculating device reputation...")
                devices = Device.query.all()
                print(f"Found {len(devices)} devices")

                for device in devices:
                    # 查询上次计算后的操作日志
                    logs = OperationLog.query.filter(
                        OperationLog.device_id == device.device_fingerprint,
                        OperationLog.create_time > device.last_calc_time
                    ).all()

                    # 计算总评分
                    total_score = sum(log.score for log in logs) if logs else 0
                    new_reputation = max(0, device.current_reputation + total_score)

                    # 更新设备信誉值与计算时间
                    device.current_reputation = new_reputation
                    device.last_calc_time = datetime.utcnow()

                    # 信誉值低于阈值：清空日志
                    if new_reputation < REPUTATION_THRESHOLD:
                        OperationLog.query.filter(
                            OperationLog.device_id == device.device_fingerprint
                        ).delete()
                        print(f"Device {device.device_fingerprint} reputation below threshold, logs cleared")

                db.session.commit()
                print(f"Reputation calculation completed at {datetime.utcnow()}")

            except Exception as e:
                print(f"Error in reputation calculation: {e}")
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
    print("Reputation calculator thread started")