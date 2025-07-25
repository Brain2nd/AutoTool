#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
快速捕获并标记所有UI组件的简单脚本
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


def quick_ui_screenshot(output_folder: str = None, max_elements: int = 150):
    """
    快速捕获UI截图并标记所有组件
    
    Args:
        output_folder: 输出目录，默认为桌面上的"UI分析"文件夹
        max_elements: 最多标记的元素数量
    """
    # 确定输出目录
    if not output_folder:
        if os.name == 'nt':  # Windows
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        else:  # Linux/Mac
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        
        output_folder = os.path.join(desktop, "UI分析")
    
    # 确保目录存在
    os.makedirs(output_folder, exist_ok=True)
    
    # 生成截图文件名
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(output_folder, f"UI_{timestamp}.png")
    
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法获取UI截图")
        return None
    
    # 执行截图并标记
    print("正在捕获并分析UI组件...")
    result = adb_tool.capture_and_mark_all_elements(
        save_path=screenshot_path,
        highlight_special=True,
        max_elements=max_elements
    )
    
    if result['success']:
        print(f"\n✓ UI分析成功")
        print(f"✓ 截图保存在: {result['marked_screenshot']}")
        
        # 显示基本统计信息
        ui_info = result['ui_info']
        elements_count = len(ui_info['elements'])
        app_name = ui_info['package_name'].split('.')[-1]  # 提取应用名称
        marked_count = result['message'].split('标记了 ')[1].split(' ')[0]  # 提取标记数量
        
        print(f"\n应用: {app_name}")
        print(f"组件总数: {elements_count}")
        print(f"已标记组件: {marked_count}")
        
        # 统计特殊元素
        clickable_count = sum(1 for e in ui_info['elements'] if e.get('clickable', False))
        scrollable_count = sum(1 for e in ui_info['elements'] if e.get('scrollable', False))
        
        print(f"可点击组件: {clickable_count}")
        print(f"可滚动组件: {scrollable_count}")
        
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
        print(f"UI分析失败: {result['message']}")
        return None


if __name__ == "__main__":
    # 如果提供了命令行参数，则使用参数作为输出目录
    output_dir = sys.argv[1] if len(sys.argv) > 1 else None
    
    # 如果提供了第二个参数，则作为最大元素数
    max_elements = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    
    quick_ui_screenshot(output_dir, max_elements) 