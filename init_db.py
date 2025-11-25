from models import db, User, AccessPolicy
from flask import Flask
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///zero_trust.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    # 1. 创建所有表
    db.create_all()

    # 2. 添加测试用户（用户名：test1，密码：123456；用户名：admin，密码：admin123）
    test_user = User(username="test1", role="normal")
    test_user.set_password("123456")
    admin_user = User(username="admin", role="admin")
    admin_user.set_password("admin123")

    # 3. 添加默认ABAC策略（仅允许内网Windows设备接入）
    policy_conditions = json.dumps({
        "ip_range": "192.168.1.0/24",
        "os_type": "Windows"
    })
    policy_permissions = json.dumps({
        "read": True,
        "write": False
    })
    default_policy = AccessPolicy(
        policy_name="默认设备策略",
        conditions=policy_conditions,
        permissions=policy_permissions
    )

    # 4. 提交数据
    db.session.add_all([test_user, admin_user, default_policy])
    db.session.commit()
    print("数据库初始化完成！")