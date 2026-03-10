#!/bin/bash
# 自动提交脚本 - 当代码变化时自动提交到GitHub

cd /home/anny/PycharmProjects/openclaw/master_control

# 检查是否有变化
if [ -n "$(git status --porcelain)" ]; then
    echo "检测到代码变化，正在提交..."
    
    # 添加所有变化
    git add -A
    
    # 获取今天日期作为提交信息
    DATE=$(date +%Y-%m-%d)
    git commit -m "update: 代码更新 $DATE"
    
    # 推送到GitHub（使用gh命令）
    git push
    
    echo "提交完成"
else
    echo "没有代码变化"
fi
