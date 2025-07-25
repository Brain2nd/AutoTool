#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
快速捕获聊天截图的简单脚本
"""

import os
import sys
import pathlib
import time

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def quick_chat_screenshot(output_folder: str = None):
    """
    快速捕获聊天截图并保存
    
    Args:
        output_folder: 输出目录，默认为桌面上的"聊天截图"文件夹
    """
    # 确定输出目录
    if not output_folder:
        if os.name == 'nt':  # Windows
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        else:  # Linux/Mac
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        
        output_folder = os.path.join(desktop, "聊天截图")
    
    # 确保目录存在
    os.makedirs(output_folder, exist_ok=True)
    
    # 生成截图文件名
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(output_folder, f"聊天_{timestamp}.png")
    
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法获取聊天截图")
        return None
    
    # 执行截图并标记
    print("正在捕获并分析聊天...")
    result = adb_tool.capture_and_mark_chat(save_path=screenshot_path)
    
    if result['success']:
        print(f"截图成功: {result['message']}")
        print(f"截图保存在: {result['marked_screenshot']}")
        
        # 显示基本统计信息
        chat_result = result['chat_result']
        app_type = chat_result['chat_app_type']
        partner = chat_result['chat_partner'] or '未知'
        msg_count = chat_result['total_messages']
        
        print(f"应用: {app_type}, 聊天对象: {partner}, 消息数: {msg_count}")
        
        # 尝试打开截图
        try:
            if os.name == 'nt':  # Windows
                os.startfile(result['marked_screenshot'])
            elif os.name == 'posix':  # Linux/Mac
                if sys.platform == 'darwin':  # Mac
                    os.system(f'open "{result["marked_screenshot"]}"')
                else:  # Linux
                    os.system(f'xdg-open "{result["marked_screenshot"]}"')
        except:
            pass
        
        return result['marked_screenshot']
    else:
        print(f"截图失败: {result['message']}")
        return None


if __name__ == "__main__":
    # 如果提供了命令行参数，则使用参数作为输出目录
    output_dir = sys.argv[1] if len(sys.argv) > 1 else None
    quick_chat_screenshot(output_dir) 