# OpenClaw 主控管理系统 更新日志

## [v0.1.0] - 2026-03-10

### 新增功能
- **机器人管理**：添加/删除/部署/监控终端物理机器人
- **用户管理**：多用户支持，角色权限（admin/operator/viewer）
- **微信授权**：终端机器人提供二维码，用户扫码授权
- **操作日志**：完整记录所有操作
- **SSH远程部署**：自动安装OpenClaw/RosClaw/微信服务
- **智能部署**：部署前检查服务状态，已安装则跳过
- **自动修复**：服务异常时自动尝试修复

### Bug修复
- 修复CLI中机器人列表显示格式错误
- 修复部署命令参数传递问题
- 修复Tab页面切换问题

### 页面优化
- SSH密码改为必填项
- 添加部署状态提醒弹窗
- 添加刷新状态按钮

---

## 功能说明

### 系统架构
```
┌─────────────────────────────────────────────┐
│           主控管理系统 (Master)              │
│  - Web管理界面 (Flask)                       │
│  - CLI命令行工具                             │
│  - SQLite数据库                              │
└─────────────────────────────────────────────┘
          │ SSH远程连接
          ▼
┌─────────────────────────────────────────────┐
│         终端物理机器人 (Agent)              │
│  - OpenClaw Agent服务                       │
│  - RosClaw Agent服务                        │
│  - 微信二维码服务                            │
└─────────────────────────────────────────────┘
```

### 使用方式

```bash
# 进入项目目录
cd /home/anny/PycharmProjects/openclaw/master_control

# 安装依赖
pip3 install -r requirements.txt

# 启动Web服务
python3 server.py

# 使用CLI
python3 cli.py add 172.16.14.52 -u root -p <password> --deploy
python3 cli.py list
python3 cli.py qr --ip 172.16.14.52
```

### API接口
- `GET /api/robots` - 获取机器人列表
- `POST /api/robots` - 添加机器人
- `POST /api/robots/<id>/deploy` - 部署到机器人
- `GET /api/robots/<id>/status` - 获取机器人状态
- `GET /api/robots/<id>/wechat_qr` - 获取微信二维码
- `GET /api/users` - 获取用户列表
- `GET /api/logs` - 获取操作日志
