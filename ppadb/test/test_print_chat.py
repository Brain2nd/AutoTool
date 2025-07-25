#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
打印聊天消息并区分发送者的简单工具
"""

import os
import sys
import pathlib
import time
import colorama
from colorama import Fore, Style

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def initialize_colorama():
    """初始化彩色终端输出"""
    colorama.init()


def print_chat_messages():
    """打印当前UI中的聊天消息"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法获取聊天消息")
        return
    
    # 获取聊天消息
    print("正在分析当前界面的聊天消息...")
    chat_result = adb_tool.get_chat_messages()
    
    if not chat_result['success']:
        print(f"分析失败: {chat_result['message']}")
        return
    
    if not chat_result['is_chat_ui']:
        print("当前界面不是聊天界面")
        return
    
    # 打印基本信息
    print("\n" + "=" * 60)
    print(f"聊天应用: {chat_result['chat_app_type']}")
    print(f"聊天对象: {chat_result['chat_partner'] or '未知'}")
    
    # 显示识别出的聊天区域
    if chat_result['chat_area']['bounds']:
        bounds = chat_result['chat_area']['bounds']
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        print(f"聊天区域: 位置={bounds}, 大小={width}x{height}")
    
    print("=" * 60 + "\n")
    
    # 打印消息
    if not chat_result['messages']:
        print("未找到任何消息")
        return
    
    # 按顺序打印消息，使用颜色区分不同发送者
    other_name = chat_result['chat_partner'] or '对方'
    
    for message in chat_result['messages']:
        text = message['text']
        sender = message['sender']
        message_type = message['type']
        
        # 构建位置标记
        position_info = ""
        if 'bounds' in message and message['bounds']:
            bounds = message['bounds']
            # 检查是否在聊天区域内
            if chat_result['chat_area']['bounds']:
                chat_area = chat_result['chat_area']['bounds']
                is_in_chat_area = (
                    chat_area[0] <= (bounds[0] + bounds[2])/2 <= chat_area[2] and
                    chat_area[1] <= (bounds[1] + bounds[3])/2 <= chat_area[3]
                )
                position_tag = "*区域内*" if is_in_chat_area else "区域外"
                position_info = f" [{position_tag}]"
        
        # 系统消息显示为黄色
        if message_type == 'system' or sender == 'system':
            print(f"{Fore.YELLOW}[系统]{position_info} {text}{Style.RESET_ALL}")
            continue
        
        # 引用消息显示为青色
        if message_type == 'quote':
            quoted_name = message['sender_name']
            quoted_text = message['quoted_text']
            print(f"{Fore.CYAN}[引用]{position_info} {quoted_name}: {quoted_text}{Style.RESET_ALL}")
            continue
        
        # 时间显示为灰色
        if message_type == 'time':
            print(f"{Fore.WHITE}[时间]{position_info} {text}{Style.RESET_ALL}")
            continue
        
        # 撤回消息显示为灰色
        if message_type == 'recall':
            print(f"{Fore.WHITE}[撤回]{position_info} {text}{Style.RESET_ALL}")
            continue
        
        # 普通文本消息
        if sender == 'self':
            # 自己发送的消息显示为绿色
            print(f"{Fore.GREEN}[我]{position_info} {text}{Style.RESET_ALL}")
        elif sender == 'other':
            # 对方发送的消息显示为蓝色
            print(f"{Fore.BLUE}[{other_name}]{position_info} {text}{Style.RESET_ALL}")
        else:
            # 未知发送者显示为白色
            print(f"{Fore.WHITE}[未知]{position_info} {text}{Style.RESET_ALL}")
    
    print("\n" + "=" * 60)
    print(f"共 {len(chat_result['messages'])} 条消息")
    print("=" * 60)


def monitor_chat(interval: int = 5, duration: int = 60):
    """
    持续监控聊天消息变化
    
    Args:
        interval: 监控间隔(秒)
        duration: 监控总时长(秒)，设为0表示持续监控直到用户中断
    """
    print(f"开始监控聊天消息 (每 {interval} 秒刷新一次)")
    print("按 Ctrl+C 终止监控\n")
    
    end_time = time.time() + duration if duration > 0 else float('inf')
    try:
        while time.time() < end_time:
            print_chat_messages()
            
            # 显示倒计时
            remaining = max(0, int(end_time - time.time())) if duration > 0 else 0
            countdown = f"({remaining}秒后结束)" if duration > 0 else "(持续监控中)"
            print(f"\n{countdown} 等待 {interval} 秒后刷新...")
            
            time.sleep(interval)
            
            # 清屏
            os.system('cls' if os.name == 'nt' else 'clear')
            
    except KeyboardInterrupt:
        print("\n监控已终止")


if __name__ == "__main__":
    # 初始化彩色终端
    initialize_colorama()
    
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        # 获取参数
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        
        # 启动监控模式
        monitor_chat(interval, duration)
    else:
        # 单次打印
        print_chat_messages() 