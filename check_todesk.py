#!/usr/bin/env python3
"""
Todesk 服务状态检查脚本
由 OpenClaw cron 调用，执行后需汇报结果
"""
import os
import subprocess
import json
from datetime import datetime

def check_todesk():
    result = subprocess.run(['ps', 'aux'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    return "ToDesk" in output

def start_todesk():
    subprocess.run(['/opt/todesk/bin/ToDesk_Service', '&'], shell=True)
    result = subprocess.run(['ps', 'aux'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    return output

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_running = check_todesk()
    
    report = {
        "task": "Todesk 状态检查",
        "timestamp": timestamp,
        "status": "ok" if is_running else "restarted",
        "message": "",
        "process_info": ""
    }
    
    if is_running:
        report["message"] = "✅ Todesk 服务运行正常"
    else:
        output = start_todesk()
        report["message"] = f"⚠️ Todesk 服务已重启\n进程信息:\n{output[:500]}"
    
    # 输出 JSON 供 OpenClaw 解析并汇报
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()
