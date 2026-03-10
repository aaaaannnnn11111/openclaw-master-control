# OpenClaw 主控管理系统

一个集中管理多个终端物理机器人上OpenClaw服务的系统。

## 功能特性

- 🤖 **机器人管理** - 添加、删除、部署、监控终端物理机器人
- 👥 **用户管理** - 多用户支持，角色权限控制（管理员/操作者/查看者）
- 📱 **微信授权** - 终端机器人提供二维码，用户扫码授权
- 📋 **操作日志** - 记录所有操作，便于审计追踪
- 🔒 **权限控制** - 细粒度权限管理

## 系统架构

```
┌─────────────────────────────────────────────┐
│           主控管理系统 (Master)                │
│  - Web管理界面 (Flask)                       │
│  - CLI命令行工具                             │
│  - SQLite数据库                              │
└─────────────────────────────────────────────┘
          │ SSH远程连接
          ▼
┌─────────────────────────────────────────────┐
│         终端物理机器人 (Agent)               │
│  - OpenClaw Agent服务                       │
│  - RosClaw Agent服务                        │
│  - 微信二维码服务                            │
└─────────────────────────────────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/aaaaannnnn11111/openclaw-master-control.git
cd openclaw-master-control
pip3 install -r requirements.txt
```

### 2. 启动主控服务

```bash
python3 server.py
```

服务将在 http://0.0.0.0:8888 启动

### 3. 添加机器人

#### 通过Web界面
访问 http://localhost:8888 添加机器人

#### 通过CLI

```bash
# 添加机器人
python3 cli.py add 172.16.14.52 -u root -p yourpassword --deploy

# 查看机器人列表
python3 cli.py list

# 获取微信二维码
python3 cli.py qr --ip 172.16.14.52

# 查看日志
python3 cli.py logs
```

## 使用流程

### 验收流程

1. **添加机器人** - 主控添加测试机器人IP: 172.16.14.52
2. **部署服务** - 自动在终端安装OpenClaw、RosClaw、微信服务
3. **获取二维码** - 通过主控获取微信授权二维码
4. **扫码授权** - 用户扫描终端机器人上的二维码授权
5. **验证功能** - 用户可以调用终端机器人的OpenClaw服务

### 新增机器人

只需提供以下信息：
- IP地址
- SSH用户名
- SSH密码或密钥

主控会自动完成：
- SSH连接并安装服务
- 配置systemd服务
- 启动所有服务
- 监控状态

## 命令参考

```bash
# 添加机器人
python3 cli.py add <IP> -u <user> -p <password>

# 部署
python3 cli.py deploy --ip <IP>

# 状态
python3 cli.py status --ip <IP>

# 微信二维码
python3 cli.py qr --ip <IP>

# 用户管理
python3 cli.py add-user <username> --role admin

# 日志
python3 cli.py logs --limit 20
```

## 目录结构

```
openclaw-master-control/
├── config.py       # 配置文件
├── models.py       # 数据库模型
├── deployer.py     # SSH部署模块
├── server.py       # Web服务
├── cli.py          # CLI工具
├── requirements.txt   # Python依赖
└── README.md          # 说明文档
```

## 配置说明

修改 `config.py` 可调整：
- 数据库路径
- 服务端口
- SSH连接参数
- 日志配置
