from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

# 1. 用户表（存储账号密码与角色）
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default="normal")  # normal/admin
    lock_time = db.Column(db.DateTime, nullable=True)  # 账号锁定时间
    login_attempts = db.Column(db.Integer, default=0)  # 密码错误次数

    # 密码加密存储
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    # 密码校验
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 2. 设备表（存储设备属性与信任状态）
class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    device_fingerprint = db.Column(db.String(64), unique=True, nullable=False)  # 设备指纹
    device_model = db.Column(db.String(50), nullable=False)  # 设备型号
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 关联用户
    ip_address = db.Column(db.String(20), nullable=False)  # 接入IP
    last_calc_time = db.Column(db.DateTime, default=datetime.utcnow)  # 上次信誉计算时间
    current_reputation = db.Column(db.Integer, default=100)  # 当前信誉值

# 3. ABAC策略表（存储访问控制规则）
class AccessPolicy(db.Model):
    __tablename__ = 'access_policies'
    id = db.Column(db.Integer, primary_key=True)
    policy_name = db.Column(db.String(50), nullable=False)
    # 策略条件（JSON格式：如{"os":"Windows","ip_range":"192.168.1.0/24"}）
    conditions = db.Column(db.Text, nullable=False)
    # 权限列表（JSON格式：如{"read":true,"write":false}）
    permissions = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)  # 新增：策略启用状态（默认启用）
    create_time = db.Column(db.DateTime, default=datetime.utcnow)  # 新增：创建时间
# 4. 操作日志表（存储操作记录与评分）
class OperationLog(db.Model):
    __tablename__ = 'operation_logs'
    id = db.Column(db.Integer, primary_key=True)
    device_fingerprint = db.Column(db.String(64), nullable=False)  # 设备指纹
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    operation = db.Column(db.String(100), nullable=False)  # 操作内容
    score = db.Column(db.Integer, nullable=False)  # 评分
    create_time = db.Column(db.DateTime, default=datetime.utcnow)