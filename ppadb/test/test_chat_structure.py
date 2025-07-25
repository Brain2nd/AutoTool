#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试基于UI树结构的聊天消息提取功能
此测试文件用于验证新改进的get_chat_messages()函数的功能
"""

import os
import sys
import pathlib
import json
import time
from pprint import pprint
from datetime import datetime

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def save_json_data(data, filename):
    """保存分析结果为JSON文件"""
    output_dir = current_dir / "chat_analysis"
    output_dir.mkdir(exist_ok=True)
    
    file_path = output_dir / filename
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return str(file_path)


def display_chat_info(chat_result):
    """展示聊天信息"""
    print("\n===== 聊天界面分析结果 =====")
    print(f"成功状态: {'成功' if chat_result['success'] else '失败'}")
    print(f"应用包名: {chat_result['package_name']}")
    print(f"应用类型: {chat_result['chat_app_type']}")
    
    # 显示聊天对象信息
    print(f"\n----- 聊天对象信息 -----")
    print(f"聊天对象: {chat_result['chat_partner']}")
    print(f"是否群聊: {'是' if chat_result['is_group_chat'] else '否'}")
    
    if chat_result['is_group_chat']:
        print(f"群人数: {chat_result['group_size']}")
        if chat_result['online_count']:
            print(f"在线人数: {chat_result['online_count']}")
    
    # 显示消息统计
    messages = chat_result['messages']
    print(f"\n----- 消息统计 ({len(messages)}条) -----")
    
    # 按发送者统计
    sender_stats = {}
    type_stats = {}
    
    for msg in messages:
        sender = msg['sender']
        msg_type = msg['type']
        
        sender_stats[sender] = sender_stats.get(sender, 0) + 1
        type_stats[msg_type] = type_stats.get(msg_type, 0) + 1
    
    print("发送者统计:")
    for sender, count in sender_stats.items():
        if sender == 'self':
            print(f"  - 我: {count}条")
        elif sender == 'other':
            # 需要更详细地统计各个发送者的消息
            # 重新计算各个发送者名称的消息数量
            sender_name_stats = {}
            for msg in messages:
                if msg['sender'] == 'other' and msg.get('sender_name'):
                    name = msg['sender_name'] if msg['sender_name'] != 'unknown' else '未知用户'
                    sender_name_stats[name] = sender_name_stats.get(name, 0) + 1
            
            # 显示各个发送者的消息数量
            if sender_name_stats:
                for name, name_count in sender_name_stats.items():
                    print(f"  - {name}: {name_count}条")
            else:
                print(f"  - 其他用户: {count}条")
        else:
            print(f"  - {sender}: {count}条")
    
    print("消息类型统计:")
    for msg_type, count in type_stats.items():
        print(f"  - {msg_type}: {count}条")
    
    # 显示部分消息示例
    print("\n----- 消息示例 -----")
    max_display = min(10, len(messages))
    
    for i, msg in enumerate(messages[:max_display]):
        # 格式化发送者显示
        if msg['sender'] == 'self':
            sender_display = "我"
        elif msg['sender'] == 'other':
            # 优先使用消息中的sender_name，而不是群聊名称
            if msg.get('sender_name') and msg['sender_name'] != 'unknown':
                sender_display = msg['sender_name']
            else:
                sender_display = "对方"
        else:
            sender_display = msg['sender']
        
        # 消息时间
        time_display = f" ({msg['time']})" if msg['time'] else ""
        
        # 消息类型和内容
        type_display = f"[{msg['type']}]" if msg['type'] != 'text' else ""
        content = msg['text']
        
        # 消息长度限制
        if len(content) > 50:
            content = content[:47] + "..."
        
        print(f"{i+1}. {sender_display}{time_display} {type_display}: {content}")
    
    # 如果有更多消息，显示省略提示
    if len(messages) > max_display:
        print(f"... 还有 {len(messages) - max_display} 条消息未显示")
    
    # 聊天区域信息
    print(f"\n----- 聊天区域信息 -----")
    bounds = chat_result['chat_area']['bounds']
    if bounds and len(bounds) == 4:
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        print(f"位置: {bounds}")
        print(f"大小: {width}x{height}")


def test_chat_structure():
    """测试基于UI树结构的聊天消息提取功能"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法进行测试")
        return
    
    print("\n===== 测试聊天结构识别 =====")
    print("请确保您的设备屏幕上已经打开了要分析的聊天界面")
    print("此测试将分析当前聊天界面的结构和消息")
    
    try:
        input("按回车键继续...")
    except KeyboardInterrupt:
        print("\n操作已取消")
        return
    
    # 获取聊天消息
    print("分析聊天界面中...")
    chat_result = adb_tool.get_chat_messages()
    
    # 检查结果
    if not chat_result['success']:
        print(f"分析失败: {chat_result['message']}")
        return
    
    if not chat_result['is_chat_ui']:
        print("当前界面不是聊天界面")
        return
    
    # 显示结果
    display_chat_info(chat_result)
    
    # 保存结果
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_analysis_{timestamp}.json"
        json_path = save_json_data(chat_result, filename)
        print(f"\n分析结果已保存到: {json_path}")
    except Exception as e:
        print(f"保存结果时出错: {e}")
    
    # 提供更多交互选项
    print("\n===== 更多选项 =====")
    print("1. 截图并标记聊天区域和消息")
    print("2. 获取完整UI树结构")
    print("3. 返回")
    
    try:
        choice = input("请选择操作(1-3): ")
        
        if choice == '1':
            print("截图并标记聊天区域...")
            # 截图并标记
            screenshot_result = adb_tool.capture_and_mark_chat()
            if screenshot_result['success']:
                print(f"截图已保存到: {screenshot_result['screenshot_path']}")
            else:
                print(f"截图失败: {screenshot_result['message']}")
                
        elif choice == '2':
            print("获取完整UI树结构...")
            ui_result = adb_tool.get_current_app_ui(pretty_print=True, save_xml=True)
            if ui_result['success']:
                print(f"UI结构已保存")
                # 保存UI树为JSON
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ui_json_path = save_json_data(ui_result, f"ui_tree_{timestamp}.json")
                print(f"UI树结构已保存到: {ui_json_path}")
            else:
                print(f"获取UI树失败: {ui_result['message']}")
    except KeyboardInterrupt:
        print("\n操作已取消")
    
    print("\n测试完成")


def main():
    """主函数"""
    test_chat_structure()


if __name__ == "__main__":
    main() 