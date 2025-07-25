#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试标记界面上所有UI组件位置的功能
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


def get_default_output_dir() -> str:
    """获取默认的输出目录（桌面上的UI分析文件夹）"""
    if os.name == 'nt':  # Windows
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    else:  # Linux/Mac
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    
    output_dir = os.path.join(desktop, "UI分析")
    return output_dir


def capture_and_mark_ui_elements(output_dir: str = None, max_elements: int = 200) -> Dict[str, Any]:
    """
    捕获屏幕截图并标记所有UI组件位置
    
    Args:
        output_dir: 输出目录，如果不指定则使用桌面上的"UI分析"文件夹
        max_elements: 最多标记的元素数量，避免过多元素导致图片混乱
        
    Returns:
        标记结果
    """
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法获取UI信息")
        return {
            'success': False,
            'message': '未连接设备'
        }
    
    # 确定输出目录
    if not output_dir:
        output_dir = get_default_output_dir()
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成截图文件名
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(output_dir, f"ui_elements_{timestamp}.png")
    
    # 捕获并标记UI元素
    print("正在捕获屏幕并分析UI组件...")
    return adb_tool.capture_and_mark_all_elements(
        save_path=screenshot_path,
        highlight_special=True,
        max_elements=max_elements
    )


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='UI组件标记工具')
    parser.add_argument('-o', '--output', type=str, default=None,
                      help='截图输出目录 (可选)')
    parser.add_argument('-m', '--max-elements', type=int, default=200,
                      help='最多标记的元素数量 (默认200)')
    parser.add_argument('-c', '--continuous', action='store_true',
                      help='连续模式，每隔指定秒数截取一次')
    parser.add_argument('-i', '--interval', type=int, default=5,
                      help='连续模式下的间隔秒数 (默认5秒)')
    parser.add_argument('-n', '--count', type=int, default=0,
                      help='连续模式下的截图次数 (默认0表示无限次)')
    parser.add_argument('-s', '--no-special', action='store_true',
                      help='不高亮特殊元素(所有元素使用相同颜色)')
    args = parser.parse_args()
    
    # 单次模式
    if not args.continuous:
        print("正在捕获并标记UI元素...")
        result = capture_and_mark_ui_elements(
            output_dir=args.output,
            max_elements=args.max_elements
        )
        
        if result['success']:
            print(f"标记成功: {result['message']}")
            print(f"标记截图: {result['marked_screenshot']}")
            
            # 显示UI统计信息
            ui_info = result['ui_info']
            elements_count = len(ui_info['elements'])
            print(f"\n应用包名: {ui_info['package_name']}")
            print(f"活动名称: {ui_info['activity_name'] if 'activity_name' in ui_info else '未知'}")
            print(f"元素总数: {elements_count}")
            
            # 显示元素类型统计
            class_counts = {}
            for element in ui_info['elements']:
                if 'class' in element:
                    class_name = element['class'].split('.')[-1]  # 只取类名的最后部分
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1
            
            print("\n元素类型统计:")
            for class_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {class_name}: {count}")
            
            # 显示交互元素统计
            clickable_count = sum(1 for e in ui_info['elements'] if e.get('clickable', False))
            scrollable_count = sum(1 for e in ui_info['elements'] if e.get('scrollable', False))
            long_clickable_count = sum(1 for e in ui_info['elements'] if e.get('long-clickable', False))
            
            print("\n交互元素统计:")
            print(f"  - 可点击元素: {clickable_count}")
            print(f"  - 可滚动元素: {scrollable_count}")
            print(f"  - 可长按元素: {long_clickable_count}")
            
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
            print(f"标记失败: {result['message']}")
    
    # 连续模式
    else:
        print(f"启动连续截图模式，间隔 {args.interval} 秒")
        print("按 Ctrl+C 终止截图")
        
        count = 0
        try:
            while args.count == 0 or count < args.count:
                # 创建带计数的文件名
                output_dir = args.output or get_default_output_dir()
                os.makedirs(output_dir, exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                save_path = os.path.join(output_dir, f"ui_elements_{timestamp}_{count+1}.png")
                
                # 执行标记
                print(f"正在进行第 {count+1} 次UI分析...")
                
                # 初始化工具
                adb_tool = PPADBTool()
                result = adb_tool.capture_and_mark_all_elements(
                    save_path=save_path,
                    highlight_special=not args.no_special,
                    max_elements=args.max_elements
                )
                
                if result['success']:
                    print(f"第 {count+1} 次分析成功: {result['marked_screenshot']}")
                else:
                    print(f"第 {count+1} 次分析失败: {result['message']}")
                
                count += 1
                
                # 如果达到指定次数，退出循环
                if args.count > 0 and count >= args.count:
                    break
                
                # 等待下一次截图
                print(f"等待 {args.interval} 秒后进行下一次分析...")
                time.sleep(args.interval)
                
        except KeyboardInterrupt:
            print("\n分析任务已终止")
        
        print(f"共完成 {count} 次UI分析")


if __name__ == "__main__":
    main() 