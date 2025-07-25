#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试聊天消息识别功能，能够区分消息发送者和引用关系
"""

import os
import sys
import pathlib
import json
import time
from typing import Dict, Any, List

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def print_separator(length: int = 60) -> None:
    """打印分隔线"""
    print("=" * length)


def analyze_chat_ui() -> Dict[str, Any]:
    """
    分析当前UI中的聊天消息
    
    Returns:
        聊天消息分析结果
    """
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法获取聊天消息")
        return {
            'success': False,
            'message': '未连接设备'
        }
    
    # 获取聊天消息
    print("正在分析当前界面的聊天消息...")
    return adb_tool.get_chat_messages()


def save_analysis_result(result: Dict[str, Any], save_dir: str = None) -> None:
    """
    保存分析结果到文件
    
    Args:
        result: 分析结果
        save_dir: 保存目录
    """
    if not result['success']:
        print(f"分析失败，不保存结果: {result['message']}")
        return
    
    # 确定保存目录
    if not save_dir:
        save_dir = os.path.join(current_dir, 'chat_analysis')
    
    # 确保目录存在
    os.makedirs(save_dir, exist_ok=True)
    
    # 生成文件名
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    result_file = os.path.join(save_dir, f'chat_analysis_{timestamp}.json')
    
    # 保存结果
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"分析结果已保存到: {result_file}")


def print_chat_messages(result: Dict[str, Any]) -> None:
    """
    打印聊天消息分析结果
    
    Args:
        result: 聊天消息分析结果
    """
    if not result['success']:
        print(f"分析失败: {result['message']}")
        return
    
    if not result['is_chat_ui']:
        print("当前界面不是聊天界面")
        return
    
    # 打印基本信息
    print_separator()
    print(f"聊天应用: {result['chat_app_type']}")
    print(f"聊天对象: {result['chat_partner']}")
    print(f"消息数量: {result['total_messages']}")
    
    # 显示识别出的聊天区域
    if result['chat_area']['bounds']:
        bounds = result['chat_area']['bounds']
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        print(f"聊天区域: 位置={bounds}, 大小={width}x{height}, 元素索引={result['chat_area']['element_index']}")
    
    print_separator()
    
    # 打印消息
    if not result['messages']:
        print("未找到任何消息")
        return
    
    # 格式化消息类型
    message_type_map = {
        'text': '文本消息',
        'quote': '引用消息',
        'system': '系统消息',
        'recall': '撤回消息',
        'time': '时间标记'
    }
    
    # 格式化发送者
    sender_map = {
        'self': '我',
        'other': result['chat_partner'] or '对方',
        'system': '系统',
        'unknown': '未知'
    }
    
    # 按时间顺序打印消息
    for i, message in enumerate(result['messages'], 1):
        sender = sender_map.get(message['sender'], message['sender_name'] or '未知')
        msg_type = message_type_map.get(message['type'], message['type'])
        
        print(f"消息 #{i} [{msg_type}]")
        print(f"发送者: {sender}")
        
        # 显示位置信息
        if 'bounds' in message and message['bounds']:
            bounds = message['bounds']
            # 检查是否在聊天区域内
            in_chat_area = "否"
            if result['chat_area']['bounds']:
                chat_area = result['chat_area']['bounds']
                is_in_chat_area = (
                    chat_area[0] <= (bounds[0] + bounds[2])/2 <= chat_area[2] and
                    chat_area[1] <= (bounds[1] + bounds[3])/2 <= chat_area[3]
                )
                in_chat_area = "是" if is_in_chat_area else "否"
            
            print(f"位置: {bounds}, 在聊天区域内: {in_chat_area}")
        
        if message['type'] == 'quote':
            print(f"引用内容: {message['quoted_text']}")
            print(f"引用者: {message['sender_name']}")
        elif message['type'] == 'text':
            print(f"内容: {message['text']}")
        else:
            print(f"内容: {message['text']}")
        
        print_separator(30)


def main():
    """主函数"""
    print("正在分析当前UI中的聊天消息...")
    
    # 执行分析
    result = analyze_chat_ui()
    
    # 显示结果
    print_chat_messages(result)
    
    # 询问是否保存结果
    save_option = input("\n是否保存分析结果? (y/n): ").lower()
    if save_option == 'y':
        save_analysis_result(result)


if __name__ == "__main__":
    main() 