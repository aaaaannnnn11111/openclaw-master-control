# -*- coding: utf-8 -*-
"""
SSH远程连接和部署模块
"""

import paramiko
import socket
import time
import uuid
import os
from pathlib import Path

class SSHClient:
    """SSH远程连接客户端"""
    
    def __init__(self, host, port=22, username=None, password=None, key_filename=None, timeout=30):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.timeout = timeout
        self.client = None
        self.sftp = None
    
    def connect(self):
        """建立SSH连接"""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        connect_kwargs = {
            'hostname': self.host,
            'port': self.port,
            'username': self.username,
            'timeout': self.timeout,
            'banner_timeout': self.timeout,
            'auth_timeout': self.timeout,
        }
        
        if self.key_filename:
            connect_kwargs['key_filename'] = self.key_filename
        elif self.password:
            connect_kwargs['password'] = self.password
        
        self.client.connect(**connect_kwargs)
        self.sftp = self.client.open_sftp()
        return self
    
    def close(self):
        """关闭连接"""
        if self.sftp:
            self.sftp.close()
        if self.client:
            self.client.close()
    
    def execute(self, command, timeout=60):
        """执行远程命令"""
        if not self.client:
            raise Exception("未连接SSH")
        
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        return {
            'exit_code': exit_code,
            'output': output,
            'error': error,
            'success': exit_code == 0
        }
    
    def upload_file(self, local_path, remote_path):
        """上传文件"""
        if not self.sftp:
            raise Exception("未连接SFTP")
        self.sftp.put(local_path, remote_path)
    
    def upload_directory(self, local_dir, remote_dir):
        """上传目录"""
        local_path = Path(local_dir)
        remote_path = Path(remote_dir)
        
        # 创建远程目录
        self.execute(f'mkdir -p {remote_path}')
        
        for item in local_path.rglob('*'):
            if item.is_file():
                rel_path = item.relative_to(local_path)
                remote_file = remote_path / rel_path
                self.execute(f'mkdir -p {remote_file.parent}')
                self.sftp.put(str(item), str(remote_file))
    
    def download_file(self, remote_path, local_path):
        """下载文件"""
        if not self.sftp:
            raise Exception("未连接SFTP")
        self.sftp.get(remote_path, local_path)
    
    def __enter__(self):
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class RobotDeployer:
    """终端物理机器人部署器"""
    
    def __init__(self, ssh_client: SSHClient):
        self.ssh = ssh_client
        self.install_path = '/opt/openclaw'
    
    def check_connection(self):
        """检查连接和系统信息"""
        result = self.ssh.execute('uname -a && python3 --version 2>/dev/null || python --version')
        return result
    
    def check_docker(self):
        """检查Docker是否安装"""
        result = self.ssh.execute('docker --version')
        return result
    
    def check_openclaw(self):
        """检查OpenClaw是否已安装"""
        result = self.ssh.execute(f'test -d {self.install_path} && echo "exists" || echo "not_exists"')
        return result['output'].strip() == 'exists'
    
    def install_dependencies(self):
        """安装系统依赖"""
        commands = [
            'apt-get update',
            'apt-get install -y python3 python3-pip python3-venv git curl wget',
            'pip3 install --upgrade pip',
        ]
        
        for cmd in commands:
            print(f"执行: {cmd}")
            result = self.ssh.execute(cmd, timeout=300)
            if not result['success']:
                print(f"警告: {result.get('error', '')}")
        return True
    
    def install_openclaw(self):
        """安装OpenClaw Agent"""
        # 创建安装目录
        self.ssh.execute(f'mkdir -p {self.install_path}')
        
        # 创建OpenClaw Agent服务脚本
        agent_script = self._get_agent_script()
        self.ssh.execute(f'cat > {self.install_path}/openclaw_agent.py << \'EOFAGENT\'\n{agent_script}\nEOFAGENT')
        
        # 创建systemd服务
        service_content = self._get_systemd_service()
        self.ssh.execute(f'cat > /etc/systemd/system/openclaw-agent.service << \'EOFSERVICE\'\n{service_content}\nEOFSERVICE')
        
        # 创建RosClaw服务脚本
        rosclaw_script = self._get_rosclaw_script()
        self.ssh.execute(f'cat > {self.install_path}/rosclaw_agent.py << \'EOFROSC\'\n{rosclaw_script}\nEOFROSC')
        
        # 创建RosClaw systemd服务
        rosclaw_service = self._get_rosclaw_systemd_service()
        self.ssh.execute(f'cat > /etc/systemd/system/rosclaw-agent.service << \'EOFROSVC\'\n{rosclaw_service}\nEOFROSVC')
        
        return True
    
    def install_wechat_qr_service(self):
        """安装微信二维码服务"""
        qr_script = self._get_wechat_qr_script()
        self.ssh.execute(f'cat > {self.install_path}/wechat_qr_service.py << \'EOFQR\'\n{qr_script}\nEOFQR')
        
        # 创建微信服务systemd
        wechat_service = self._get_wechat_systemd_service()
        self.ssh.execute(f'cat > /etc/systemd/system/openclaw-wechat.service << \'EOFWE\'\n{wechat_service}\nEOFWE')
        
        return True
    
    def start_services(self):
        """启动所有服务"""
        commands = [
            'systemctl daemon-reload',
            'systemctl enable openclaw-agent',
            'systemctl enable rosclaw-agent',
            'systemctl enable openclaw-wechat',
            'systemctl restart openclaw-agent',
            'systemctl restart rosclaw-agent',
            'systemctl restart openclaw-wechat',
        ]
        
        for cmd in commands:
            print(f"执行: {cmd}")
            result = self.ssh.execute(cmd, timeout=60)
            if not result['success']:
                print(f"警告: {result.get('error', '')}")
        
        return True
    
    def stop_services(self):
        """停止所有服务"""
        commands = [
            'systemctl stop openclaw-agent',
            'systemctl stop rosclaw-agent',
            'systemctl stop openclaw-wechat',
        ]
        
        for cmd in commands:
            self.ssh.execute(cmd, timeout=30)
        
        return True
    
    def restart_services(self):
        """重启所有服务"""
        commands = [
            'systemctl restart openclaw-agent',
            'systemctl restart rosclaw-agent',
            'systemctl restart openclaw-wechat',
        ]
        
        for cmd in commands:
            result = self.ssh.execute(cmd, timeout=60)
            if not result['success']:
                print(f"警告: {result.get('error', '')}")
        
        return True
    
    def get_service_status(self):
        """获取服务状态"""
        services = ['openclaw-agent', 'rosclaw-agent', 'openclaw-wechat']
        status = {}
        
        for svc in services:
            result = self.ssh.execute(f'systemctl is-active {svc} 2>/dev/null || echo "unknown"')
            status[svc] = result['output'].strip()
        
        return status
    
    def check_and_fix_services(self):
        """检查服务状态并尝试修复问题"""
        print("=== 检查服务状态 ===")
        
        results = {
            'checked': [],
            'fixed': [],
            'failed': [],
            'already_ok': []
        }
        
        # 1. 检查OpenClaw是否已安装
        installed = self.check_openclaw()
        results['checked'].append(('openclaw_installed', installed))
        
        if not installed:
            print("[!] OpenClaw未安装，开始安装...")
            self.install_dependencies()
            self.install_openclaw()
            self.install_wechat_qr_service()
            results['fixed'].append('openclaw_installed')
        
        # 2. 检查各服务状态
        services = ['openclaw-agent', 'rosclaw-agent', 'openclaw-wechat']
        
        for svc in services:
            result = self.ssh.execute(f'systemctl is-active {svc} 2>/dev/null || echo "unknown"')
            status = result['output'].strip()
            results['checked'].append((svc, status))
            
            if status == 'active':
                print(f"✅ {svc}: 运行中")
                results['already_ok'].append(svc)
            elif status == 'failed':
                print(f"❌ {svc}: 启动失败，尝试修复...")
                # 查看错误日志
                log_result = self.ssh.execute(f'journalctl -u {svc} -n 10 --no-pager 2>/dev/null || echo "无法获取日志"')
                print(f"   日志: {log_result['output'][:200]}...")
                
                # 尝试重启服务
                restart_result = self.ssh.execute(f'systemctl restart {svc}', timeout=30)
                if restart_result['success']:
                    # 等待一下再检查
                    self.ssh.execute('sleep 2')
                    check = self.ssh.execute(f'systemctl is-active {svc}')
                    if check['output'].strip() == 'active':
                        print(f"✅ {svc}: 修复成功")
                        results['fixed'].append(svc)
                    else:
                        print(f"❌ {svc}: 修复失败")
                        results['failed'].append(svc)
                else:
                    print(f"❌ {svc}: 修复失败")
                    results['failed'].append(svc)
            else:
                # 服务未启动，尝试启动
                print(f"⚠️ {svc}: 未运行，尝试启动...")
                start_result = self.ssh.execute(f'systemctl start {svc}', timeout=30)
                if start_result['success']:
                    self.ssh.execute('sleep 2')
                    check = self.ssh.execute(f'systemctl is-active {svc}')
                    if check['output'].strip() == 'active':
                        print(f"✅ {svc}: 启动成功")
                        results['fixed'].append(svc)
                    else:
                        results['failed'].append(svc)
                else:
                    results['failed'].append(svc)
        
        # 3. 确保服务开机自启
        for svc in services:
            self.ssh.execute(f'systemctl enable {svc}', timeout=30)
        
        # 4. 获取最终状态
        final_status = self.get_service_status()
        
        return {
            'success': len(results['failed']) == 0,
            'results': results,
            'final_status': final_status
        }
    
    def get_wechat_qr(self):
        """获取微信二维码"""
        # 从服务获取二维码
        result = self.ssh.execute('cat /opt/openclaw/wechat_qr_code.png 2>/dev/null | base64 | head -1')
        if result['success']:
            return result['output'].strip()
        return None
    
    def full_deploy(self, smart_check=True):
        """完整部署流程
        
        Args:
            smart_check: 是否启用智能检查（检查服务状态并修复）
        """
        print(f"=== 开始部署到 {self.ssh.host} ===")
        
        # 1. 检查连接
        print("\n[1/5] 检查连接...")
        info = self.check_connection()
        print(info['output'])
        
        if smart_check:
            # 智能检查：检查服务状态并修复
            print("\n[2/5] 智能检查服务状态...")
            check_result = self.check_and_fix_services()
            
            print("\n[3/5] 检查结果:")
            print(f"  ✅ 正常: {check_result['results'].get('already_ok', [])}")
            print(f"  🔧 已修复: {check_result['results'].get('fixed', [])}")
            print(f"  ❌ 失败: {check_result['results'].get('failed', [])}")
            
            if check_result['success']:
                print("\n✅ 所有服务正常运行!")
            else:
                print("\n⚠️ 部分服务存在问题，请检查!")
            
            final_status = check_result['final_status']
        else:
            # 传统方式：直接安装
            print("\n[2/5] 检查OpenClaw...")
            if self.check_openclaw():
                print("OpenClaw已安装，跳过安装步骤")
            else:
                print("安装OpenClaw...")
                self.install_dependencies()
                self.install_openclaw()
            
            # 3. 安装微信服务
            print("\n[3/5] 安装微信二维码服务...")
            self.install_wechat_qr_service()
            
            # 4. 启动服务
            print("\n[4/5] 启动服务...")
            self.start_services()
            
            # 5. 检查状态
            print("\n[5/5] 检查服务状态...")
            final_status = self.get_service_status()
            for svc, s in final_status.items():
                print(f"  {svc}: {s}")
        
        print("\n=== 部署完成 ===")
        return {
            'success': True,
            'status': final_status
        }
    
    def _get_agent_script(self):
        """获取OpenClaw Agent脚本"""
        return '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Agent - 运行在终端物理机器人上
"""

import sys
import os
import time
import socket
import threading
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# 配置日志
LOG_FILE = '/var/log/openclaw/agent.log'
os.makedirs('/var/log/openclaw', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

class OpenClawAgent:
    def __init__(self, port=8888):
        self.port = port
        self.master_host = None
        self.robot_id = None
        self.status = 'idle'
        self.users = []
    
    def register_to_master(self, master_url):
        """向主控注册"""
        # TODO: 实现向主控注册的逻辑
        pass
    
    def start(self):
        """启动Agent"""
        logging.info(f"OpenClaw Agent 启动，端口: {self.port}")
        self.status = 'running'
        self.start_http_server()
    
    def start_http_server(self):
        """启动HTTP服务"""
        server = HTTPServer(('0.0.0.0', self.port), AgentRequestHandler)
        logging.info(f"HTTP服务运行在端口 {self.port}")
        server.serve_forever()

class AgentRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'status': 'running',
                'timestamp': datetime.now().isoformat(),
                'robot_id': 'unknown'
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        logging.info(f"{self.client_address[0]} - {format % args}")

def main():
    agent = OpenClawAgent(port=int(os.environ.get('OPENCLAW_PORT', 8888)))
    agent.start()

if __name__ == '__main__':
    main()
'''
    
    def _get_systemd_service(self):
        """获取OpenClaw Agent systemd服务文件"""
        return '''[Unit]
Description=OpenClaw Agent Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/openclaw
ExecStart=/usr/bin/python3 /opt/openclaw/openclaw_agent.py
Restart=always
RestartSec=10
Environment=OPENCLAW_PORT=8888

[Install]
WantedBy=multi-user.target
'''
    
    def _get_rosclaw_script(self):
        """获取RosClaw Agent脚本"""
        return '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RosClaw Agent - ROS相关服务
"""

import sys
import os
import time
import logging
from datetime import datetime

LOG_FILE = '/var/log/openclaw/rosclaw.log'
os.makedirs('/var/log/openclaw', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

class RosClawAgent:
    def __init__(self):
        self.status = 'stopped'
    
    def start(self):
        logging.info("RosClaw Agent 启动")
        self.status = 'running'
        # TODO: 实现ROS相关功能
        while self.status == 'running':
            time.sleep(10)
    
    def stop(self):
        self.status = 'stopped'
        logging.info("RosClaw Agent 停止")

def main():
    agent = RosClawAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()

if __name__ == '__main__':
    main()
'''
    
    def _get_rosclaw_systemd_service(self):
        """获取RosClaw systemd服务文件"""
        return '''[Unit]
Description=RosClaw Agent Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/openclaw
ExecStart=/usr/bin/python3 /opt/openclaw/rosclaw_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
'''
    
    def _get_wechat_qr_script(self):
        """获取微信二维码服务脚本"""
        return '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信二维码授权服务
"""

import os
import sys
import time
import json
import logging
import uuid
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from urllib.parse import parse_qs

# 配置日志
LOG_FILE = '/var/log/openclaw/wechat.log'
QR_FILE = '/opt/openclaw/wechat_qr_code.png'
os.makedirs('/var/log/openclaw', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

class WechatQRService:
    def __init__(self, port=8889):
        self.port = port
        self.qr_tokens = {}  # token -> {expire_time, authorized_users}
        self.current_token = str(uuid.uuid4())
        self.qr_code_base64 = None
        self._generate_qr_code()
    
    def _generate_qr_code(self):
        """生成微信二维码（模拟）"""
        try:
            import qrcode
            import io
            
            # 生成二维码内容（实际应该是微信授权URL）
            qr_data = f"https://open.weixin.qq.com/connect/qrconf?scene=1&robot_id=172.16.14.52&token={self.current_token}"
            
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # 保存到文件
            img.save(QR_FILE)
            
            # 转换为base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            self.qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            logging.info(f"微信二维码已生成，Token: {self.current_token}")
            
        except ImportError:
            # 如果没有qrcode库，创建一个占位文件
            logging.warning("qrcode库未安装，创建占位二维码")
            self.qr_code_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            # 创建一个简单的占位文件
            with open(QR_FILE, 'wb') as f:
                f.write(base64.b64decode(self.qr_code_base64))
    
    def get_qr_code(self):
        """获取二维码"""
        if not self.qr_code_base64:
            self._generate_qr_code()
        return self.qr_code_base64
    
    def verify_auth(self, token, wechat_openid):
        """验证授权"""
        if token not in self.qr_tokens:
            return False
        
        token_info = self.qr_tokens[token]
        if datetime.now() > token_info['expire_time']:
            del self.qr_tokens[token]
            return False
        
        # 添加授权用户
        if wechat_openid not in token_info['authorized_users']:
            token_info['authorized_users'].append(wechat_openid)
        
        return True
    
    def start(self):
        """启动服务"""
        logging.info(f"微信二维码服务启动，端口: {self.port}")
        
        # 设置token过期时间（30分钟）
        self.qr_tokens[self.current_token] = {
            'expire_time': datetime.now() + timedelta(minutes=30),
            'authorized_users': []
        }
        
        server = HTTPServer(('0.0.0.0', self.port), WechatRequestHandler)
        server.wechat_service = self
        logging.info(f"微信服务运行在端口 {self.port}")
        server.serve_forever()

class WechatRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        service = self.server.wechat_service
        
        if self.path == '/qrcode':
            # 返回二维码
            qr_base64 = service.get_qr_code()
            self.send_response(200)
            self.send_header('Content-type', 'image/png')
            self.send_header('Content-Transfer-Encoding', 'base64')
            self.end_headers()
            self.wfile.write(qr_base64.encode())
            
        elif self.path == '/qrcode_base64':
            # 返回base64编码的二维码
            qr_base64 = service.get_qr_code()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'qr_code': f"data:image/png;base64,{qr_base64}",
                'token': service.current_token,
                'expire_minutes': 30
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'status': 'running',
                'token': service.current_token,
                'timestamp': datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        logging.info(f"{self.client_address[0]} - {format % args}")

def main():
    port = int(os.environ.get('WECHAT_QR_PORT', 8889))
    service = WechatQRService(port=port)
    service.start()

if __name__ == '__main__':
    main()
'''
    
    def _get_wechat_systemd_service(self):
        """获取微信服务的systemd文件"""
        return '''[Unit]
Description=OpenClaw WeChat QR Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/openclaw
ExecStart=/usr/bin/python3 /opt/openclaw/wechat_qr_service.py
Restart=always
RestartSec=10
Environment=WECHAT_QR_PORT=8889

[Install]
WantedBy=multi-user.target
'''

def create_deployer(host, username, password=None, key_filename=None, port=22):
    """创建部署器"""
    ssh = SSHClient(host, port, username, password, key_filename)
    return RobotDeployer(ssh)

if __name__ == '__main__':
    # 测试
    print("SSH部署模块测试")
