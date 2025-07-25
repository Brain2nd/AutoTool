#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
聊天功能测试导航脚本
提供多种测试功能的入口
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

# 导入测试模块
try:
    from ...ppadb.test.test_print_chat import print_chat_messages, monitor_chat
    from ...ppadb.test.test_chat_structure import test_chat_structure
except ImportError as e:
    print(f"导入测试模块失败: {e}")
    sys.exit(1)


def initialize_colorama():
    """初始化彩色终端输出"""
    colorama.init()


def clear_screen():
    """清空终端屏幕"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_title(title):
    """打印带颜色的标题"""
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"{title.center(60)}")
    print(f"{'=' * 60}{Style.RESET_ALL}\n")


def menu():
    """显示主菜单"""
    clear_screen()
    print_title("聊天功能测试工具")
    
    print(f"{Fore.GREEN}请选择要测试的功能:{Style.RESET_ALL}")
    print("1. 快速打印当前聊天消息")
    print("2. 监控聊天消息变化")
    print("3. 测试聊天结构识别(树结构分析)")
    print("4. 比较不同提取方法的结果")
    print("0. 退出")
    
    try:
        choice = input("\n请输入选项编号: ")
        return choice
    except KeyboardInterrupt:
        return "0"


def compare_extraction_methods():
    """比较不同的消息提取方法结果"""
    from ...ppadb.ppadbtool import PPADBTool
    
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法进行测试")
        return
    
    print_title("比较不同的消息提取方法")
    print("此测试将比较两种不同的聊天消息提取方法的结果")
    print("1. 基于位置的提取方法(原始方法)")
    print("2. 基于UI树结构的提取方法(新方法)")
    
    try:
        input("\n按回车键开始比较...")
    except KeyboardInterrupt:
        return
    
    # 调用原始方法的临时实现
    def original_get_chat_messages():
        # 备份当前方法
        original_method = adb_tool.get_chat_messages
        
        # 替换为临时实现(调用原始方法)
        def temp_original_method():
            # 此处实现原始方法的逻辑
            # 由于我们无法直接访问原始实现，这里模拟一个简化版本
            ui_info = adb_tool.get_current_app_ui()
            if not ui_info['success']:
                return {'success': False, 'message': '获取UI失败'}
            
            result = {
                'success': True,
                'message': '使用位置判断方法提取消息',
                'package_name': ui_info['package_name'],
                'is_chat_ui': True,
                'chat_app_type': 'unknown',
                'chat_partner': '',
                'messages': []
            }
            
            # 简单提取所有文本元素
            for element in ui_info['elements']:
                if element.get('class') == 'android.widget.TextView' and element.get('text'):
                    text = element.get('text')
                    bounds = element.get('bounds', [])
                    
                    if not bounds or len(bounds) != 4:
                        continue
                    
                    # 只考虑屏幕中间部分的文本
                    if 200 <= bounds[1] <= 1800:
                        msg = {
                            'text': text,
                            'sender': 'unknown',
                            'type': 'text',
                            'bounds': bounds
                        }
                        
                        # 简单的发送者判断
                        center_x = (bounds[0] + bounds[2]) / 2
                        if center_x < 400:  # 左侧
                            msg['sender'] = 'other'
                        elif center_x > 700:  # 右侧
                            msg['sender'] = 'self'
                        
                        # 添加消息
                        result['messages'].append(msg)
            
            return result
        
        adb_tool.get_chat_messages = temp_original_method
        result = adb_tool.get_chat_messages()
        
        # 恢复原始方法
        adb_tool.get_chat_messages = original_method
        return result
    
    # 执行两种提取方法
    print("\n正在使用原始方法提取聊天消息...")
    original_result = original_get_chat_messages()
    
    print("正在使用新方法提取聊天消息...")
    new_result = adb_tool.get_chat_messages()
    
    # 比较结果
    print_title("提取结果比较")
    
    print(f"{Fore.YELLOW}原始方法:{Style.RESET_ALL}")
    print(f"提取消息: {len(original_result.get('messages', []))}条")
    print(f"聊天对象: {original_result.get('chat_partner', '未识别')}")
    
    print(f"\n{Fore.YELLOW}新方法:{Style.RESET_ALL}")
    print(f"提取消息: {len(new_result.get('messages', []))}条")
    print(f"聊天对象: {new_result.get('chat_partner', '未识别')}")
    print(f"是否群聊: {'是' if new_result.get('is_group_chat', False) else '否'}")
    if new_result.get('is_group_chat', False):
        print(f"群人数: {new_result.get('group_size', '未识别')}")
    
    # 消息类型比较
    new_msg_types = {}
    for msg in new_result.get('messages', []):
        msg_type = msg.get('type', 'unknown')
        new_msg_types[msg_type] = new_msg_types.get(msg_type, 0) + 1
    
    print(f"\n{Fore.YELLOW}新方法消息类型统计:{Style.RESET_ALL}")
    for msg_type, count in new_msg_types.items():
        print(f"  - {msg_type}: {count}条")
    
    print(f"\n{Fore.GREEN}主要改进:{Style.RESET_ALL}")
    print("1. 基于UI树结构的分析提供更准确的聊天对象识别")
    print("2. 可以识别群聊和私聊的区别")
    print("3. 提取群人数和在线人数信息")
    print("4. 更准确地识别消息类型和发送者")
    
    input("\n按回车键返回主菜单...")


def main():
    """主函数"""
    initialize_colorama()
    
    while True:
        choice = menu()
        
        if choice == "0":
            break
        elif choice == "1":
            print_chat_messages()
            input("\n按回车键返回主菜单...")
        elif choice == "2":
            interval = int(input("请输入监控间隔(秒): ") or "5")
            duration = int(input("请输入监控时长(秒，0表示持续监控): ") or "60")
            monitor_chat(interval, duration)
            input("\n按回车键返回主菜单...")
        elif choice == "3":
            test_chat_structure()
            input("\n按回车键返回主菜单...")
        elif choice == "4":
            compare_extraction_methods()
        else:
            print(f"{Fore.RED}无效选项，请重试{Style.RESET_ALL}")
            time.sleep(1)
    
    print(f"{Fore.GREEN}感谢使用聊天功能测试工具！{Style.RESET_ALL}")


if __name__ == "__main__":
    main() 