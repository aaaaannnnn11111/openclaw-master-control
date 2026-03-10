# -*- coding: utf-8 -*-
"""
OpenClaw 主控管理系统 - Web API服务
"""

import os
import sys
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import (
    init_db, RobotDB, UserDB, RobotUserDB, LogDB, WechatAuthDB
)
from deployer import create_deployer

app = Flask(__name__)
CORS(app)

# 初始化数据库
init_db()

# ============== 页面模板 ==============

INDEX_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw 主控管理系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
        .header h1 { font-size: 24px; }
        .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
        .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card h2 { color: #333; margin-bottom: 15px; font-size: 18px; }
        .btn { background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .btn:hover { background: #5568d3; }
        .btn-success { background: #10b981; }
        .btn-danger { background: #ef4444; }
        .btn-sm { padding: 6px 12px; font-size: 12px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f9fafb; font-weight: 600; color: #374151; }
        .status { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .status-online { background: #d1fae5; color: #065f46; }
        .status-offline { background: #fee2e2; color: #991b1b; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #374151; font-weight: 500; }
        .form-group input { width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 14px; }
        .tabs { display: flex; border-bottom: 2px solid #e5e7eb; margin-bottom: 20px; }
        .tab { padding: 10px 20px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; }
        .tab.active { border-bottom-color: #667eea; color: #667eea; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .robot-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 15px; }
        .robot-card h3 { color: #111; margin-bottom: 10px; }
        .robot-info { color: #6b7280; font-size: 14px; }
        .robot-actions { margin-top: 15px; display: flex; gap: 10px; }
        .modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); align-items: center; justify-content: center; }
        .modal.active { display: flex; }
        .modal-content { background: white; border-radius: 8px; padding: 20px; max-width: 500px; width: 90%; max-height: 80vh; overflow-y: auto; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .modal-header h3 { color: #111; }
        .close { cursor: pointer; font-size: 24px; color: #6b7280; }
        .alert { padding: 12px; border-radius: 4px; margin-bottom: 15px; }
        .alert-success { background: #d1fae5; color: #065f46; }
        .alert-error { background: #fee2e2; color: #991b1b; }
        .alert-info { background: #dbeafe; color: #1e40af; }
        .alert-warning { background: #fef3c7; color: #92400e; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 OpenClaw 主控管理系统</h1>
    </div>
    
    <div class="container">
        <div class="tabs">
            <div class="tab active" data-tab="robots">机器人管理</div>
            <div class="tab" data-tab="users">用户管理</div>
            <div class="tab" data-tab="logs">操作日志</div>
        </div>
        
        <!-- 机器人管理 -->
        <div class="tab-content active" id="tab-robots">
            <div class="card">
                <h2>添加新机器人</h2>
                <form id="addRobotForm">
                    <div class="grid">
                        <div class="form-group">
                            <label>IP地址 *</label>
                            <input type="text" name="ip" required placeholder="如: 172.16.14.52">
                        </div>
                        <div class="form-group">
                            <label>主机名</label>
                            <input type="text" name="hostname" placeholder="可选">
                        </div>
                        <div class="form-group">
                            <label>SSH用户名 *</label>
                            <input type="text" name="ssh_user" required placeholder="如: root">
                        </div>
                        <div class="form-group">
                            <label>SSH密码 *</label>
                            <input type="password" name="ssh_password" required placeholder="必填">
                        </div>
                    </div>
                    <button type="submit" class="btn">添加并部署</button>
                </form>
            </div>
            
            <div class="card">
                <h2>机器人列表</h2>
                <div id="robotList" class="grid"></div>
            </div>
        </div>
        
        <!-- 用户管理 -->
        <div class="tab-content" id="tab-users">
            <div class="card">
                <h2>用户列表</h2>
                <div id="userList"></div>
            </div>
        </div>
        
        <!-- 操作日志 -->
        <div class="tab-content" id="tab-logs">
            <div class="card">
                <h2>操作日志</h2>
                <div id="logList"></div>
            </div>
        </div>
    </div>
    
    <!-- 添加用户弹窗 -->
    <div class="modal" id="addUserModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>添加用户</h3>
                <span class="close" onclick="closeModal('addUserModal')">&times;</span>
            </div>
            <form id="addUserForm">
                <input type="hidden" name="robot_id" id="robotIdInput">
                <div class="form-group">
                    <label>用户名</label>
                    <input type="text" name="username" required>
                </div>
                <div class="form-group">
                    <label>昵称</label>
                    <input type="text" name="nickname">
                </div>
                <div class="form-group">
                    <label>角色</label>
                    <select name="role" style="width:100%;padding:8px;">
                        <option value="viewer">查看者</option>
                        <option value="operator">操作者</option>
                        <option value="admin">管理员</option>
                    </select>
                </div>
                <button type="submit" class="btn">添加用户</button>
            </form>
        </div>
    </div>

    <script>
        // Tab切换
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
            });
        });
        
        // 加载机器人
        async function loadRobots() {
            const res = await fetch('/api/robots');
            const data = await res.json();
            const container = document.getElementById('robotList');
            if (data.robots.length === 0) {
                container.innerHTML = '<p>暂无机器人，请添加</p>';
                return;
            }
            container.innerHTML = data.robots.map(r => `
                <div class="robot-card">
                    <h3>${r.hostname || r.ip}</h3>
                    <div class="robot-info">
                        <p>IP: ${r.ip}</p>
                        <p>SSH: ${r.ssh_user}@${r.ip}</p>
                        <p>状态: <span class="status ${r.status === 'online' ? 'status-online' : 'status-offline'}">${r.status}</span></p>
                        <p>最后在线: ${r.last_online || '-'}</p>
                    </div>
                    <div class="robot-actions">
                        <button class="btn btn-sm btn-success" onclick="deployRobot(${r.id})">部署</button>
                        <button class="btn btn-sm" onclick="checkStatus(${r.id})">刷新状态</button>
                        <button class="btn btn-sm" onclick="getWechatQR(${r.id})">微信二维码</button>
                        <button class="btn btn-sm" onclick="showAddUser(${r.id})">添加用户</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteRobot(${r.id})">删除</button>
                    </div>
                </div>
            `).join('');
        }
        
        // 加载用户
        async function loadUsers() {
            const res = await fetch('/api/users');
            const data = await res.json();
            const container = document.getElementById('userList');
            if (data.users.length === 0) {
                container.innerHTML = '<p>暂无用户</p>';
                return;
            }
            container.innerHTML = `
                <table>
                    <thead><tr><th>ID</th><th>用户名</th><th>昵称</th><th>微信</th><th>角色</th><th>状态</th></tr></thead>
                    <tbody>
                        ${data.users.map(u => `
                            <tr>
                                <td>${u.id}</td>
                                <td>${u.username}</td>
                                <td>u.nickname || '-'</td>
                                <td>${u.wechat_nickname || '-'}</td>
                                <td>${u.role}</td>
                                <td>${u.status}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
        
        // 加载日志
        async function loadLogs() {
            const res = await fetch('/api/logs');
            const data = await res.json();
            const container = document.getElementById('logList');
            if (data.logs.length === 0) {
                container.innerHTML = '<p>暂无日志</p>';
                return;
            }
            container.innerHTML = `
                <table>
                    <thead><tr><th>时间</th><th>操作</th><th>详情</th><th>结果</th></tr></thead>
                    <tbody>
                        ${data.logs.map(l => `
                            <tr>
                                <td>${l.created_at}</td>
                                <td>${l.action}</td>
                                <td>${l.detail || '-'}</td>
                                <td>${l.result}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        }
        
        // 添加机器人
        document.getElementById('addRobotForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            const res = await fetch('/api/robots', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            alert(result.message);
            if (result.success) {
                loadRobots();
                e.target.reset();
            }
        };
        
        // 部署机器人
        async function deployRobot(id) {
            if (!confirm('确认部署到该机器人？')) return;
            
            // 显示部署中
            showAlert('正在部署，请稍候...', 'info');
            
            const res = await fetch(`/api/robots/${id}/deploy`, {method: 'POST'});
            const result = await res.json();
            
            if (result.success) {
                // 显示详细状态
                let msg = '✅ 部署完成!\n\n服务状态:\n';
                if (result.status_messages) {
                    msg += result.status_messages.join('\n');
                }
                alert(msg);
                loadRobots();
            } else {
                alert('❌ ' + result.message);
            }
        }
        
        // 显示提醒
        function showAlert(message, type = 'success') {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type}`;
            alertDiv.textContent = message;
            alertDiv.style.cssText = 'position:fixed;top:20px;right:20px;z-index:1000;min-width:300px;';
            
            const container = document.querySelector('.container');
            container.insertBefore(alertDiv, container.firstChild);
            
            // 5秒后自动消失
            setTimeout(() => alertDiv.remove(), 5000);
        }
        
        // 检查机器人状态
        async function checkStatus(id) {
            showAlert('正在检查状态...', 'info');
            
            const res = await fetch(`/api/robots/${id}/status`);
            const result = await res.json();
            
            if (result.success) {
                let msg = '服务状态:\n';
                for (const [svc, status] of Object.entries(result.status)) {
                    msg += `${status === 'active' ? '✅' : '❌'} ${svc}: ${status}\n`;
                }
                alert(msg);
                loadRobots();
            } else {
                alert('❌ ' + result.message);
            }
        }
        
        // 获取微信二维码
        async function getWechatQR(id) {
            const res = await fetch(`/api/robots/${id}/wechat_qr`);
            const result = await res.json();
            if (result.success) {
                const win = window.open('', '_blank', 'width=400,height=500');
                win.document.write(`
                    <html><head><title>微信扫码授权</title></head>
                    <body style="text-align:center;padding:50px;">
                        <h2>请扫码授权</h2>
                        <img src="${result.qr_code}" style="max-width:300px;">
                        <p>Token: ${result.token}</p>
                        <p>有效期: 30分钟</p>
                    </body></html>
                `);
            } else {
                alert(result.message);
            }
        }
        
        // 删除机器人
        async function deleteRobot(id) {
            if (!confirm('确认删除该机器人？')) return;
            
            const res = await fetch(`/api/robots/${id}`, {method: 'DELETE'});
            const result = await res.json();
            alert(result.message);
            if (result.success) loadRobots();
        }
        
        // 显示添加用户弹窗
        function showAddUser(robotId) {
            document.getElementById('robotIdInput').value = robotId;
            document.getElementById('addUserModal').classList.add('active');
        }
        
        // 关闭弹窗
        function closeModal(id) {
            document.getElementById(id).classList.remove('active');
        }
        
        // 添加用户
        document.getElementById('addUserForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            data.robot_id = parseInt(data.robot_id);
            
            const res = await fetch('/api/users', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            alert(result.message);
            if (result.success) {
                closeModal('addUserModal');
                e.target.reset();
            }
        };
        
        // 初始化
        loadRobots();
        loadUsers();
        loadLogs();
    </script>
</body>
</html>
'''

# ============== API路由 ==============

@app.route('/')
def index():
    """主页"""
    return render_template_string(INDEX_HTML)

@app.route('/api/robots', methods=['GET', 'POST'])
def robots():
    """机器人列表/添加"""
    if request.method == 'GET':
        robots = RobotDB.get_all_robots()
        return jsonify({'success': True, 'robots': robots})
    
    # POST: 添加机器人
    data = request.json
    try:
        robot_id = RobotDB.add_robot(
            ip=data['ip'],
            hostname=data.get('hostname'),
            ssh_user=data['ssh_user'],
            ssh_password=data.get('ssh_password'),
            ssh_key_path=data.get('ssh_key_path')
        )
        
        # 记录日志
        LogDB.add_log(
            robot_id=robot_id,
            user_id=None,
            action='add_robot',
            detail=f"添加机器人: {data['ip']}"
        )
        
        return jsonify({'success': True, 'message': '机器人添加成功', 'robot_id': robot_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/robots/<int:robot_id>', methods=['GET', 'DELETE'])
def robot_detail(robot_id):
    """机器人详情/删除"""
    if request.method == 'DELETE':
        try:
            RobotDB.delete_robot(robot_id)
            LogDB.add_log(robot_id=robot_id, user_id=None, action='delete_robot', detail=f"删除机器人ID: {robot_id}")
            return jsonify({'success': True, 'message': '机器人已删除'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    robot = RobotDB.get_robot(robot_id)
    if not robot:
        return jsonify({'success': False, 'message': '机器人不存在'})
    return jsonify({'success': True, 'robot': robot})

@app.route('/api/robots/<int:robot_id>/deploy', methods=['POST'])
def deploy_robot(robot_id):
    """部署到机器人"""
    robot = RobotDB.get_robot(robot_id)
    if not robot:
        return jsonify({'success': False, 'message': '机器人不存在'})
    
    try:
        # 创建SSH连接
        deployer = create_deployer(
            host=robot['ip'],
            username=robot['ssh_user'],
            password=robot['ssh_password'],
            key_filename=robot['ssh_key_path']
        )
        
        with deployer.ssh as ssh:
            # 执行部署（启用智能检查）
            result = deployer.full_deploy(smart_check=True)
        
        # 解析服务状态
        status = result.get('status', {})
        check_result = result.get('check_result', {})
        
        # 生成状态消息
        status_messages = []
        for svc, svc_status in status.items():
            if svc_status == 'active':
                status_messages.append(f"✅ {svc}: 运行中")
            else:
                status_messages.append(f"❌ {svc}: {svc_status}")
        
        # 更新状态
        RobotDB.update_robot_status(robot_id, 'online', last_online=datetime.now().isoformat())
        
        # 记录日志
        LogDB.add_log(
            robot_id=robot_id,
            user_id=None,
            action='deploy',
            detail=f"部署到 {robot['ip']} - " + ", ".join(status_messages),
            result='success'
        )
        
        return jsonify({
            'success': True, 
            'message': '部署完成',
            'status': status,
            'status_messages': status_messages
        })
    
    except Exception as e:
        LogDB.add_log(
            robot_id=robot_id,
            user_id=None,
            action='deploy',
            detail=f"部署失败: {str(e)}",
            result='failed'
        )
        return jsonify({'success': False, 'message': f'部署失败: {str(e)}'})

@app.route('/api/robots/<int:robot_id>/status', methods=['GET'])
def robot_status(robot_id):
    """获取机器人状态"""
    robot = RobotDB.get_robot(robot_id)
    if not robot:
        return jsonify({'success': False, 'message': '机器人不存在'})
    
    try:
        deployer = create_deployer(
            host=robot['ip'],
            username=robot['ssh_user'],
            password=robot['ssh_password'],
            key_filename=robot['ssh_key_path']
        )
        
        with deployer.ssh as ssh:
            status = deployer.get_service_status()
        
        RobotDB.update_robot_status(robot_id, 'online', last_online=datetime.now().isoformat())
        return jsonify({'success': True, 'status': status})
    
    except Exception as e:
        RobotDB.update_robot_status(robot_id, 'offline')
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/robots/<int:robot_id>/wechat_qr', methods=['GET'])
def robot_wechat_qr(robot_id):
    """获取微信二维码"""
    robot = RobotDB.get_robot(robot_id)
    if not robot:
        return jsonify({'success': False, 'message': '机器人不存在'})
    
    try:
        deployer = create_deployer(
            host=robot['ip'],
            username=robot['ssh_user'],
            password=robot['ssh_password'],
            key_filename=robot['ssh_key_path']
        )
        
        with deployer.ssh as ssh:
            result = ssh.execute(f"curl -s http://localhost:{robot.get('wechat_port', 8889)}/qrcode_base64")
        
        if result['success']:
            qr_data = json.loads(result['output'])
            return jsonify({
                'success': True,
                'qr_code': qr_data.get('qr_code'),
                'token': qr_data.get('token')
            })
        else:
            return jsonify({'success': False, 'message': '无法获取二维码'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/robots/<int:robot_id>/users', methods=['GET'])
def robot_users(robot_id):
    """获取机器人用户列表"""
    users = RobotUserDB.get_robot_users(robot_id)
    return jsonify({'success': True, 'users': users})

@app.route('/api/robots/<int:robot_id>/users', methods=['POST'])
def add_robot_user(robot_id):
    """添加用户到机器人"""
    data = request.json
    
    # 创建或获取用户
    user = UserDB.get_user(username=data['username'])
    if not user:
        user_id = UserDB.add_user(
            username=data['username'],
            nickname=data.get('nickname'),
            role=data.get('role', 'viewer')
        )
    else:
        user_id = user['id']
    
    # 绑定用户到机器人
    RobotUserDB.bind_user(robot_id, user_id, permissions='[]')
    
    # 记录日志
    LogDB.add_log(
        robot_id=robot_id,
        user_id=user_id,
        action='add_user',
        detail=f"添加用户: {data['username']}"
    )
    
    return jsonify({'success': True, 'message': '用户添加成功'})

# ============== 用户API ==============

@app.route('/api/users', methods=['GET', 'POST'])
def users():
    """用户列表/添加"""
    if request.method == 'GET':
        users = UserDB.get_all_users()
        return jsonify({'success': True, 'users': users})
    
    data = request.json
    try:
        user_id = UserDB.add_user(
            username=data['username'],
            nickname=data.get('nickname'),
            role=data.get('role', 'viewer')
        )
        return jsonify({'success': True, 'message': '用户添加成功', 'user_id': user_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/users/<int:user_id>', methods=['GET', 'DELETE'])
def user_detail(user_id):
    """用户详情/删除"""
    if request.method == 'DELETE':
        # TODO: 实现删除
        return jsonify({'success': True, 'message': '用户已删除'})
    
    user = UserDB.get_user(user_id=user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'})
    return jsonify({'success': True, 'user': user})

# ============== 日志API ==============

@app.route('/api/logs', methods=['GET'])
def logs():
    """操作日志"""
    robot_id = request.args.get('robot_id', type=int)
    user_id = request.args.get('user_id', type=int)
    limit = request.args.get('limit', 100, type=int)
    
    logs = LogDB.get_logs(robot_id=robot_id, user_id=user_id, limit=limit)
    return jsonify({'success': True, 'logs': logs})

# ============== 主控管理API ==============

@app.route('/api/master/status', methods=['GET'])
def master_status():
    """主控状态"""
    robots = RobotDB.get_all_robots()
    users = UserDB.get_all_users()
    
    online_count = sum(1 for r in robots if r['status'] == 'online')
    
    return jsonify({
        'success': True,
        'status': {
            'total_robots': len(robots),
            'online_robots': online_count,
            'total_users': len(users),
            'timestamp': datetime.now().isoformat()
        }
    })

def run_server(host='0.0.0.0', port=8888):
    """运行服务器"""
    print(f"OpenClaw 主控管理系统启动: http://{host}:{port}")
    app.run(host=host, port=port, debug=True)

if __name__ == '__main__':
    run_server()
