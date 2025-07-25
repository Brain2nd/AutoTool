#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试聊天截图标记功能，能够捕获屏幕并标记聊天区域和消息位置
"""

import os
import sys
import pathlib
import time
import argparse
from typing import Dict, Any

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def capture_and_mark_chat(output_dir: str = None) -> Dict[str, Any]:
    """
    捕获屏幕截图并标记聊天消息
    
    Args:
        output_dir: 输出目录，如果不指定则使用临时目录
        
    Returns:
        标记结果
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
    
    # 创建输出目录（如果指定）
    save_path = None
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(output_dir, f"chat_marked_{timestamp}.png")
    
    # 捕获并标记聊天
    print("正在捕获屏幕并分析聊天...")
    return adb_tool.capture_and_mark_chat(save_path=save_path)


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='聊天截图标记工具')
    parser.add_argument('-o', '--output', type=str, default=None,
                       help='截图输出目录 (可选)')
    parser.add_argument('-c', '--continuous', action='store_true',
                       help='连续模式，每隔指定秒数截取一次')
    parser.add_argument('-i', '--interval', type=int, default=5,
                       help='连续模式下的间隔秒数 (默认5秒)')
    parser.add_argument('-n', '--count', type=int, default=0,
                       help='连续模式下的截图次数 (默认0表示无限次)')
    args = parser.parse_args()
    
    # 单次模式
    if not args.continuous:
        print("正在捕获并标记聊天截图...")
        result = capture_and_mark_chat(args.output)
        
        if result['success']:
            print(f"截图成功: {result['message']}")
            print(f"原始截图: {result['original_screenshot']}")
            print(f"标记截图: {result['marked_screenshot']}")
            
            # 显示聊天统计信息
            chat_result = result['chat_result']
            print(f"\n聊天应用: {chat_result['chat_app_type']}")
            print(f"聊天对象: {chat_result['chat_partner'] or '未知'}")
            print(f"识别消息数: {chat_result['total_messages']}")
            
            # 尝试使用系统默认应用打开标记后的截图
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(result['marked_screenshot'])
                elif os.name == 'posix':  # Linux/Mac
                    if sys.platform == 'darwin':  # Mac
                        os.system(f'open "{result["marked_screenshot"]}"')
                    else:  # Linux
                        os.system(f'xdg-open "{result["marked_screenshot"]}"')
            except:
                print("\n请手动打开截图查看结果")
        else:
            print(f"截图失败: {result['message']}")
    
    # 连续模式
    else:
        print(f"启动连续截图模式，间隔 {args.interval} 秒")
        print("按 Ctrl+C 终止截图")
        
        count = 0
        try:
            while args.count == 0 or count < args.count:
                # 创建带计数的文件名
                save_path = None
                if args.output:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    save_path = os.path.join(args.output, f"chat_marked_{timestamp}_{count+1}.png")
                
                # 执行截图
                result = capture_and_mark_chat(save_path)
                
                if result['success']:
                    print(f"第 {count+1} 次截图成功: {result['marked_screenshot']}")
                else:
                    print(f"第 {count+1} 次截图失败: {result['message']}")
                
                count += 1
                
                # 如果达到指定次数，退出循环
                if args.count > 0 and count >= args.count:
                    break
                
                # 等待下一次截图
                print(f"等待 {args.interval} 秒后进行下一次截图...")
                time.sleep(args.interval)
                
        except KeyboardInterrupt:
            print("\n截图任务已终止")
        
        print(f"共完成 {count} 次截图")


if __name__ == "__main__":
    main() 