from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from models import db, User, Device, OperationLog
from device_utils import collect_device_attrs, get_client_ip
from policy_utils import match_abac_policy
from reputation_utils import start_reputation_calculator
from datetime import datetime, timedelta
import jwt
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///zero_trust.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 创建数据库表
with app.app_context():
    db.create_all()
    # 启动信誉值计算线程，传递 app 实例
    start_reputation_calculator(app)  # 这里添加 app 参数

# ---------------- 页面路由 ----------------
@app.route('/')
def index():
    """设备接入首页"""
    return render_template('index.html')

@app.route('/login/<device_fingerprint>')
def login(device_fingerprint):
    """登录页面"""
    session['device_fingerprint'] = device_fingerprint
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """操作面板（可视化）"""
    # 验证令牌
    token = session.get('token')
    if not token:
        return redirect(url_for('index'))
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = payload['user_id']
        device_fingerprint = session.get('device_fingerprint')

        # 获取设备信誉值与操作日志
        device = Device.query.filter_by(device_fingerprint=device_fingerprint).first()
        logs = OperationLog.query.filter_by(
            device_id=device_fingerprint,
            user_id=user_id
        ).order_by(OperationLog.create_time.desc()).limit(10).all()

        return render_template('dashboard.html',
                               reputation=device.current_reputation if device else 0,
                               logs=logs)
    except:
        return redirect(url_for('index'))

# ---------------- API接口 ----------------
@app.route('/api/device/register', methods=['POST'])
def device_register():
    """设备注册与属性校验"""
    data = request.json
    device_model = data.get('device_model')
    if not device_model:
        return jsonify({"code": 400, "msg": "请输入设备型号"})

    # 1. 采集设备属性
    device_attrs = collect_device_attrs(device_model)
    # 2. ABAC策略匹配
    policy_matched, permissions = match_abac_policy(device_attrs)
    if not policy_matched:
        return jsonify({"code": 403, "msg": "设备不合法（IP/类型不符）", "data": {}})

    # 3. 设备入库（若已存在则更新）
    device = Device.query.filter_by(device_fingerprint=device_attrs["device_fingerprint"]).first()
    if not device:
        device = Device(
            device_fingerprint=device_attrs["device_fingerprint"],
            device_model=device_attrs["device_model"],
            ip_address=device_attrs["ip_address"],
            current_reputation=100
        )
        db.session.add(device)
    db.session.commit()

    return jsonify({
        "code": 200,
        "msg": "设备校验通过",
        "data": {
            "device_fingerprint": device_attrs["device_fingerprint"],
            "permissions": permissions
        }
    })

@app.route('/api/user/login', methods=['POST'])
def user_login():
    """用户身份认证"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    device_fingerprint = session.get('device_fingerprint')

    # 1. 查找用户
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"code": 401, "msg": "用户名不存在"})

    # 2. 检查账号锁定
    if user.lock_time and datetime.utcnow() < user.lock_time + timedelta(minutes=10):
        return jsonify({"code": 403, "msg": "账号已锁定，请10分钟后重试"})

    # 3. 校验密码
    if not user.check_password(password):
        user.login_attempts += 1
        # 3次错误锁定账号
        if user.login_attempts >= 3:
            user.lock_time = datetime.utcnow()
        db.session.commit()
        return jsonify({"code": 401, "msg": f"密码错误，剩余{3 - user.login_attempts}次机会"})

    # 4. 重置登录状态
    user.login_attempts = 0
    user.lock_time = None
    db.session.commit()

    # 5. 生成JWT令牌
    token = jwt.encode(
        {"user_id": user.id, "exp": datetime.utcnow() + timedelta(hours=1)},
        app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    session['token'] = token

    return jsonify({"code": 200, "msg": "登录成功", "data": {"token": token}})

@app.route('/api/operation/log', methods=['POST'])
def log_operation():
    """记录操作并评分"""
    data = request.json
    operation = data.get('operation')
    is_legal = data.get('is_legal', True)

    # 验证令牌
    token = session.get('token')
    if not token:
        return jsonify({"code": 401, "msg": "未登录"})
    payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
    user_id = payload['user_id']
    device_fingerprint = session.get('device_fingerprint')

    # 评分规则
    score = 10 if is_legal else -50

    # 记录日志
    log = OperationLog(
        device_id=device_fingerprint,
        user_id=user_id,
        operation=operation,
        score=score
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({"code": 200, "msg": "操作已记录"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)