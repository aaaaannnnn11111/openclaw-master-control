#!/bin/bash
# OpenClaw 主控管理系统安装脚本

set -e

echo "========================================"
echo "  OpenClaw 主控管理系统安装"
echo "========================================"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

echo "✅ Python3 已安装: $(python3 --version)"

# 安装依赖
echo ""
echo "正在安装依赖..."

pip3 install -q flask flask-cors paramiko qrcode

echo "✅ 依赖安装完成"

# 创建目录
mkdir -p /home/anny/.openclaw/logs

echo ""
echo "========================================"
echo "  安装完成!"
echo "========================================"
echo ""
echo "启动主控服务:"
echo "  cd /home/anny/PycharmProjects/openclaw"
echo "  python3 master_control/server.py"
echo ""
echo "或使用CLI工具:"
echo "  python3 master_control/cli.py -h"
echo ""
