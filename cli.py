#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw 主控管理CLI工具
"""

import os
import sys
import argparse
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import init_db, RobotDB, UserDB, RobotUserDB, LogDB
from deployer import create_deployer

def cmd_add_robot(args):
    """添加机器人"""
    robot_id = RobotDB.add_robot(
        ip=args.ip,
        hostname=args.hostname,
        ssh_user=args.ssh_user,
        ssh_password=args.password,
        ssh_key_path=args.key
    )
    print(f"✅ 机器人添加成功 (ID: {robot_id})")
    
    if args.deploy:
        cmd_deploy_robot(robot_id, args)
    
    return robot_id

def cmd_deploy_robot(robot_id, args=None):
    """部署到机器人"""
    robot = RobotDB.get_robot(robot_id)
    if not robot:
        print(f"❌ 机器人 {robot_id} 不存在")
        return False
    
    print(f"🚀 开始部署到 {robot['ip']}...")
    
    try:
        deployer = create_deployer(
            host=robot['ip'],
            username=robot['ssh_user'],
            password=robot['ssh_password'],
            key_filename=robot['ssh_key_path']
        )
        
        with deployer.ssh as ssh:
            deployer.full_deploy()
        
        RobotDB.update_robot_status(robot_id, 'online')
        print(f"✅ 部署成功!")
        return True
        
    except Exception as e:
        print(f"❌ 部署失败: {e}")
        RobotDB.update_robot_status(robot_id, 'offline')
        return False

def cmd_list_robots(args):
    """列出所有机器人"""
    robots = RobotDB.get_all_robots()
    
    if not robots:
        print("暂无机器人")
        return
    
    print(f"\n{'ID':<5} {'IP':<20} {'主机名':<20} {'状态':<10} {'最后在线':<20}")
    print("-" * 80)
    
    for r in robots:
        print(f"{r['id']:<5} {r['ip']:<20} {r.get('hostname') or '-':<20} {r['status']:<10} {r.get('last_online') or '-':<20}")

def cmd_robot_status(args):
    """获取机器人状态"""
    if args.ip:
        robot = RobotDB.get_robot(ip=args.ip)
    else:
        robot = RobotDB.get_robot(robot_id=args.id)
    
    if not robot:
        print("❌ 机器人不存在")
        return
    
    print(f"\n=== 机器人状态: {robot['ip']} ===")
    print(f"主机名: {robot.get('hostname', '-')}")
    print(f"SSH用户: {robot['ssh_user']}")
    print(f"状态: {robot['status']}")
    print(f"最后在线: {robot.get('last_online', '-')}")
    
    # 尝试获取实时状态
    try:
        deployer = create_deployer(
            host=robot['ip'],
            username=robot['ssh_user'],
            password=robot['ssh_password'],
            key_filename=robot['ssh_key_path']
        )
        
        with deployer.ssh as ssh:
            status = deployer.get_service_status()
        
        print("\n服务状态:")
        for svc, s in status.items():
            print(f"  {svc}: {s}")
        
        RobotDB.update_robot_status(robot['id'], 'online')
        
    except Exception as e:
        print(f"\n⚠️ 无法获取实时状态: {e}")
        RobotDB.update_robot_status(robot['id'], 'offline')

def cmd_wechat_qr(args):
    """获取微信二维码"""
    if args.ip:
        robot = RobotDB.get_robot(ip=args.ip)
    else:
        robot = RobotDB.get_robot(robot_id=args.id)
    
    if not robot:
        print("❌ 机器人不存在")
        return
    
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
            print(f"\n✅ 获取成功!")
            print(f"Token: {qr_data.get('token')}")
            print(f"有效期: {qr_data.get('expire_minutes')}分钟")
            print(f"\n二维码URL:")
            print(qr_data.get('qr_code', '')[:100] + "...")
        else:
            print("❌ 无法获取二维码")
            
    except Exception as e:
        print(f"❌ 获取失败: {e}")

def cmd_add_user(args):
    """添加用户"""
    user_id = UserDB.add_user(
        username=args.username,
        nickname=args.nickname,
        role=args.role
    )
    print(f"✅ 用户添加成功 (ID: {user_id})")
    
    if args.robot:
        robot = RobotDB.get_robot(ip=args.robot) or RobotDB.get_robot(robot_id=args.robot)
        if robot:
            RobotUserDB.bind_user(robot['id'], user_id)
            print(f"✅ 用户已绑定到机器人 {robot['ip']}")

def cmd_list_users(args):
    """列出所有用户"""
    users = UserDB.get_all_users()
    
    if not users:
        print("暂无用户")
        return
    
    print(f"\n{'ID':<5} {'用户名':<20} {'昵称':<20} {'微信':<20} {'角色':<10}")
    print("-" * 80)
    
    for u in users:
        print(f"{u['id']:<5} {u['username']:<20} {u.get('nickname', '-'):<20} {u.get('wechat_nickname', '-'):<20} {u['role']:<10}")

def cmd_list_logs(args):
    """列出日志"""
    logs = LogDB.get_logs(robot_id=args.robot_id, user_id=args.user_id, limit=args.limit)
    
    if not logs:
        print("暂无日志")
        return
    
    print(f"\n{'时间':<25} {'操作':<20} {'详情':<30} {'结果':<10}")
    print("-" * 90)
    
    for log in logs:
        detail = (log.get('detail') or '-')[:28]
        print(f"{log['created_at']:<25} {log['action']:<20} {detail:<30} {log['result']:<10}")

def cmd_delete_robot(args):
    """删除机器人"""
    if args.ip:
        robot = RobotDB.get_robot(ip=args.ip)
    else:
        robot = RobotDB.get_robot(robot_id=args.id)
    
    if not robot:
        print("❌ 机器人不存在")
        return
    
    confirm = input(f"确认删除机器人 {robot['ip']}? (y/n): ")
    if confirm.lower() == 'y':
        RobotDB.delete_robot(robot['id'])
        print("✅ 机器人已删除")

def main():
    parser = argparse.ArgumentParser(description='OpenClaw 主控管理工具')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 添加机器人
    add_parser = subparsers.add_parser('add', help='添加机器人')
    add_parser.add_argument('ip', help='机器人IP地址')
    add_parser.add_argument('--hostname', help='主机名')
    add_parser.add_argument('--ssh-user', '-u', default='root', help='SSH用户名')
    add_parser.add_argument('--password', '-p', help='SSH密码')
    add_parser.add_argument('--key', '-k', help='SSH密钥路径')
    add_parser.add_argument('--deploy', '-d', action='store_true', help='添加后立即部署')
    
    # 部署
    deploy_parser = subparsers.add_parser('deploy', help='部署到机器人')
    deploy_parser.add_argument('--ip', help='机器人IP')
    deploy_parser.add_argument('--id', type=int, help='机器人ID')
    
    # 列表
    subparsers.add_parser('list', help='列出所有机器人')
    
    # 状态
    status_parser = subparsers.add_parser('status', help='获取机器人状态')
    status_parser.add_argument('--ip', help='机器人IP')
    status_parser.add_argument('--id', type=int, help='机器人ID')
    
    # 微信二维码
    qr_parser = subparsers.add_parser('qr', help='获取微信二维码')
    qr_parser.add_argument('--ip', help='机器人IP')
    qr_parser.add_argument('--id', type=int, help='机器人ID')
    
    # 添加用户
    user_parser = subparsers.add_parser('add-user', help='添加用户')
    user_parser.add_argument('username', help='用户名')
    user_parser.add_argument('--nickname', '-n', help='昵称')
    user_parser.add_argument('--role', '-r', default='viewer', choices=['admin', 'operator', 'viewer'], help='角色')
    user_parser.add_argument('--robot', help='绑定到机器人IP或ID')
    
    # 用户列表
    subparsers.add_parser('list-users', help='列出所有用户')
    
    # 日志
    log_parser = subparsers.add_parser('logs', help='查看日志')
    log_parser.add_argument('--robot-id', type=int, help='机器人ID过滤')
    log_parser.add_argument('--user-id', type=int, help='用户ID过滤')
    log_parser.add_argument('--limit', type=int, default=50, help='显示条数')
    
    # 删除
    delete_parser = subparsers.add_parser('delete', help='删除机器人')
    delete_parser.add_argument('--ip', help='机器人IP')
    delete_parser.add_argument('--id', type=int, help='机器人ID')
    
    args = parser.parse_args()
    
    # 初始化数据库
    init_db()
    
    # 执行命令
    if args.command == 'add':
        cmd_add_robot(args)
    elif args.command == 'deploy':
        if not args.ip and not args.id:
            print("错误: 需要指定 --ip 或 --id")
            sys.exit(1)
        if args.ip:
            robot = RobotDB.get_robot(ip=args.ip)
        else:
            robot = RobotDB.get_robot(robot_id=args.id)
        if robot:
            cmd_deploy_robot(robot['id'], args)
        else:
            print("❌ 机器人不存在")
    elif args.command == 'list':
        cmd_list_robots(args)
    elif args.command == 'status':
        if not args.ip and not args.id:
            print("错误: 需要指定 --ip 或 --id")
            sys.exit(1)
        cmd_robot_status(args)
    elif args.command == 'qr':
        if not args.ip and not args.id:
            print("错误: 需要指定 --ip 或 --id")
            sys.exit(1)
        cmd_wechat_qr(args)
    elif args.command == 'add-user':
        cmd_add_user(args)
    elif args.command == 'list-users':
        cmd_list_users(args)
    elif args.command == 'logs':
        cmd_list_logs(args)
    elif args.command == 'delete':
        if not args.ip and not args.id:
            print("错误: 需要指定 --ip 或 --id")
            sys.exit(1)
        cmd_delete_robot(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
