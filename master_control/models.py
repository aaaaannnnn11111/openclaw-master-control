# -*- coding: utf-8 -*-
"""
OpenClaw 主控管理系统 - 数据库模型
"""

import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 
                       'openclaw_master.db')

@contextmanager
def get_db():
    """数据库上下文管理器"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """初始化数据库表"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 机器人表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS robots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip VARCHAR(50) UNIQUE NOT NULL,
                hostname VARCHAR(100),
                ssh_user VARCHAR(50),
                ssh_password TEXT,
                ssh_key_path TEXT,
                status VARCHAR(20) DEFAULT 'offline',
                openclaw_port INTEGER DEFAULT 8888,
                wechat_port INTEGER DEFAULT 8889,
                ros_status VARCHAR(20) DEFAULT 'stopped',
                last_online DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                nickname VARCHAR(100),
                wechat_openid VARCHAR(100) UNIQUE,
                wechat_nickname VARCHAR(100),
                avatar_url TEXT,
                role VARCHAR(20) DEFAULT 'viewer',
                status VARCHAR(20) DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 机器人-用户关联表（多对多）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS robot_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                permissions TEXT,  -- JSON格式存储权限列表
                wechat_auth_time DATETIME,
                auth_status VARCHAR(20) DEFAULT 'pending',
                last_active DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (robot_id) REFERENCES robots(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(robot_id, user_id)
            )
        ''')
        
        # 操作日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id INTEGER,
                user_id INTEGER,
                action VARCHAR(50) NOT NULL,
                detail TEXT,
                ip_address VARCHAR(50),
                result VARCHAR(20) DEFAULT 'success',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (robot_id) REFERENCES robots(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # 微信授权表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wechat_auth (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id INTEGER NOT NULL,
                qr_code_token VARCHAR(100) UNIQUE,
                qr_code_url TEXT,
                expire_time DATETIME,
                scan_count INTEGER DEFAULT 0,
                authorized_users TEXT,  -- JSON格式
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (robot_id) REFERENCES robots(id)
            )
        ''')

class RobotDB:
    """机器人数据库操作"""
    
    @staticmethod
    def add_robot(ip, ssh_user, ssh_password=None, ssh_key_path=None, hostname=None):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO robots (ip, hostname, ssh_user, ssh_password, ssh_key_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (ip, hostname, ssh_user, ssh_password, ssh_key_path))
            return cursor.lastrowid
    
    @staticmethod
    def get_robot(robot_id=None, ip=None):
        with get_db() as conn:
            cursor = conn.cursor()
            if robot_id:
                cursor.execute('SELECT * FROM robots WHERE id = ?', (robot_id,))
            else:
                cursor.execute('SELECT * FROM robots WHERE ip = ?', (ip,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_all_robots():
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM robots ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def update_robot_status(robot_id, status, **kwargs):
        with get_db() as conn:
            cursor = conn.cursor()
            fields = ['status = ?']
            values = [status]
            for k, v in kwargs.items():
                fields.append(f'{k} = ?')
                values.append(v)
            values.append(robot_id)
            cursor.execute(f'UPDATE robots SET {", ".join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', values)
    
    @staticmethod
    def delete_robot(robot_id):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM robot_users WHERE robot_id = ?', (robot_id,))
            cursor.execute('DELETE FROM operation_logs WHERE robot_id = ?', (robot_id,))
            cursor.execute('DELETE FROM wechat_auth WHERE robot_id = ?', (robot_id,))
            cursor.execute('DELETE FROM robots WHERE id = ?', (robot_id,))

class UserDB:
    """用户数据库操作"""
    
    @staticmethod
    def add_user(username, nickname=None, wechat_openid=None, wechat_nickname=None, role='viewer'):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, nickname, wechat_openid, wechat_nickname, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, nickname, wechat_openid, wechat_nickname, role))
            return cursor.lastrowid
    
    @staticmethod
    def get_user(user_id=None, username=None, wechat_openid=None):
        with get_db() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            elif username:
                cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            elif wechat_openid:
                cursor.execute('SELECT * FROM users WHERE wechat_openid = ?', (wechat_openid,))
            else:
                return None
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_all_users():
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def update_user(user_id, **kwargs):
        with get_db() as conn:
            cursor = conn.cursor()
            fields = []
            values = []
            for k, v in kwargs.items():
                fields.append(f'{k} = ?')
                values.append(v)
            values.append(user_id)
            if fields:
                cursor.execute(f'UPDATE users SET {", ".join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', values)
    
    @staticmethod
    def bind_wechat(user_id, wechat_openid, wechat_nickname=None):
        UserDB.update_user(user_id, wechat_openid=wechat_openid, wechat_nickname=wechat_nickname)

class RobotUserDB:
    """机器人-用户关联操作"""
    
    @staticmethod
    def bind_user(robot_id, user_id, permissions='[]'):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO robot_users (robot_id, user_id, permissions, wechat_auth_time, auth_status)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'authorized')
            ''', (robot_id, user_id, permissions))
    
    @staticmethod
    def unbind_user(robot_id, user_id):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM robot_users WHERE robot_id = ? AND user_id = ?', (robot_id, user_id))
    
    @staticmethod
    def get_robot_users(robot_id):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.*, ru.permissions, ru.auth_status, ru.wechat_auth_time, ru.last_active
                FROM users u
                JOIN robot_users ru ON u.id = ru.user_id
                WHERE ru.robot_id = ?
            ''', (robot_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_user_robots(user_id):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, ru.permissions, ru.auth_status, ru.wechat_auth_time
                FROM robots r
                JOIN robot_users ru ON r.id = ru.robot_id
                WHERE ru.user_id = ? AND ru.auth_status = 'authorized'
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def update_permissions(robot_id, user_id, permissions):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE robot_users SET permissions = ?, last_active = CURRENT_TIMESTAMP
                WHERE robot_id = ? AND user_id = ?
            ''', (json.dumps(permissions), robot_id, user_id))

class LogDB:
    """操作日志数据库操作"""
    
    @staticmethod
    def add_log(robot_id, user_id, action, detail=None, result='success', ip_address=None):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO operation_logs (robot_id, user_id, action, detail, result, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (robot_id, user_id, action, detail, result, ip_address))
    
    @staticmethod
    def get_logs(robot_id=None, user_id=None, limit=100):
        with get_db() as conn:
            cursor = conn.cursor()
            sql = 'SELECT * FROM operation_logs WHERE 1=1'
            params = []
            if robot_id:
                sql += ' AND robot_id = ?'
                params.append(robot_id)
            if user_id:
                sql += ' AND user_id = ?'
                params.append(user_id)
            sql += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

class WechatAuthDB:
    """微信授权数据库操作"""
    
    @staticmethod
    def create_auth(robot_id, qr_code_token, qr_code_url, expire_minutes=30):
        expire_time = datetime.now().timestamp() + expire_minutes * 60
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO wechat_auth (robot_id, qr_code_token, qr_code_url, expire_time)
                VALUES (?, ?, ?, ?)
            ''', (robot_id, qr_code_token, qr_code_url, datetime.fromtimestamp(expire_time)))
            return cursor.lastrowid
    
    @staticmethod
    def get_auth(qr_code_token):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM wechat_auth WHERE qr_code_token = ?', (qr_code_token,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def update_auth(qr_code_token, authorized_users=None, scan_count=None):
        with get_db() as conn:
            cursor = conn.cursor()
            fields = []
            values = []
            if authorized_users is not None:
                fields.append('authorized_users = ?')
                values.append(json.dumps(authorized_users))
            if scan_count is not None:
                fields.append('scan_count = ?')
                values.append(scan_count + 1)  # 简化处理
            values.append(qr_code_token)
            if fields:
                cursor.execute(f'UPDATE wechat_auth SET {", ".join(fields)} WHERE qr_code_token = ?', values)

if __name__ == '__main__':
    # 初始化数据库
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    init_db()
    print(f"数据库初始化完成: {DB_PATH}")
