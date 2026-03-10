# -*- coding: utf-8 -*-
"""
OpenClaw 主控管理系统配置
"""

# ============== 数据库配置 ==============
DATABASE = {
    'type': 'sqlite',
    'path': 'master_control/openclaw_master.db'
}

# ============== 主控服务配置 ==============
MASTER_CONFIG = {
    'host': '0.0.0.0',
    'port': 8888,
    'debug': True
}

# ============== SSH连接配置 ==============
SSH_CONFIG = {
    'timeout': 30,
    'banner_timeout': 30,
    'auth_timeout': 30,
    'port': 22,
    'username': 'root',  # 默认用户名，会被覆盖
    'password': None,    # 密码或使用密钥
    'key_filename': None  # SSH密钥路径
}

# ============== OpenClaw安装配置 ==============
OPENCLAW_INSTALL = {
    'install_path': '/opt/openclaw',
    'service_name': 'openclaw-agent',
    'rosclaw_service_name': 'rosclaw-agent',
    'wechat_qr_port': 8889  # 微信二维码服务端口
}

# ============== 用户权限配置 ==============
PERMISSIONS = {
    'admin': ['*'],  # 所有权限
    'operator': ['control', 'view_log', 'view_status'],
    'viewer': ['view_status', 'view_log']
}

# ============== 日志配置 ==============
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'max_days': 30
}
