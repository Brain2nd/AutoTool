#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试分析应用UI结构功能
"""

import os
import sys
import pathlib
import json
import time
from datetime import datetime

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def save_pretty_ui_summary(ui_result, output_file):
    """
    保存格式化的UI分析摘要
    
    Args:
        ui_result: UI分析结果
        output_file: 输出文件路径
    """
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("===== UI分析摘要 =====\n\n")
        f.write(f"应用包名: {ui_result['package_name']}\n")
        f.write(f"活动名称: {ui_result['activity_name']}\n")
        f.write(f"元素总数: {len(ui_result['elements'])}\n\n")
        
        # 元素类型统计
        class_count = {}
        for element in ui_result['elements']:
            class_name = element.get('class', 'unknown')
            class_count[class_name] = class_count.get(class_name, 0) + 1
        
        f.write("元素类型统计:\n")
        for class_name, count in sorted(class_count.items(), key=lambda x: x[1], reverse=True):
            f.write(f"- {class_name}: {count}\n")
        
        f.write("\n可交互元素统计:\n")
        # 统计可点击元素
        clickable_count = sum(1 for e in ui_result['elements'] if e.get('clickable', False))
        f.write(f"- 可点击元素: {clickable_count}\n")
        
        # 统计可长按元素
        long_clickable_count = sum(1 for e in ui_result['elements'] if e.get('long-clickable', False))
        f.write(f"- 可长按元素: {long_clickable_count}\n")
        
        # 统计可滚动元素
        scrollable_count = sum(1 for e in ui_result['elements'] if e.get('scrollable', False))
        f.write(f"- 可滚动元素: {scrollable_count}\n")
        
        # 统计文本元素
        text_elements = [e for e in ui_result['elements'] if e.get('text') and e['text'].strip()]
        f.write(f"- 包含文本的元素: {len(text_elements)}\n\n")
        
        # 显示可点击元素的详细信息
        f.write("===== 可点击元素详情 =====\n\n")
        clickable_elements = [e for e in ui_result['elements'] if e.get('clickable', False)]
        for i, element in enumerate(clickable_elements, 1):
            text = element.get('text', '')
            desc = element.get('content-desc', '')
            res_id = element.get('resource-id', '')
            class_name = element.get('class', '')
            bounds = element.get('bounds', [])
            
            f.write(f"元素 {i}:\n")
            f.write(f"- 类型: {class_name}\n")
            if text:
                f.write(f"- 文本: {text}\n")
            if desc:
                f.write(f"- 描述: {desc}\n")
            if res_id:
                f.write(f"- ID: {res_id}\n")
            if bounds:
                f.write(f"- 位置: {bounds}\n")
            f.write("\n")


def test_analyze_ui():
    """测试分析应用UI结构功能"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法进行测试")
        return
    
    # 创建输出目录
    output_dir = current_dir / "ui_analysis"
    output_dir.mkdir(exist_ok=True)
    
    # 准备获取当前页面UI
    print("\n===== 开始分析当前界面UI结构 =====\n")
    print("请确保您的设备屏幕上已经打开了要分析的应用")
    
    try:
        input("按回车键继续...")
    except KeyboardInterrupt:
        print("\n操作已取消")
        return
    
    # 生成XML保存路径
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xml_path = output_dir / f"ui_dump_{timestamp}.xml"
    
    # 获取UI结构
    print("正在获取UI结构...")
    ui_result = adb_tool.get_current_app_ui(
        pretty_print=True,
        save_xml=True,
        save_path=str(xml_path)
    )
    
    if not ui_result['success']:
        print(f"分析UI结构失败: {ui_result['message']}")
        return
    
    # 保存完整结果为JSON
    json_path = output_dir / f"ui_analysis_{timestamp}.json"
    
    # 不保存完整XML，它可能会很大
    xml_content = ui_result.pop('xml')
    ui_result['xml'] = '(XML内容已保存到单独文件)'
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ui_result, f, ensure_ascii=False, indent=2)
    
    # 保存格式化的UI摘要
    summary_path = output_dir / f"ui_summary_{timestamp}.txt"
    save_pretty_ui_summary(ui_result, summary_path)
    
    # 显示结果
    print(f"\n分析成功: {ui_result['message']}")
    print(f"应用包名: {ui_result['package_name']}")
    print(f"活动名称: {ui_result['activity_name']}")
    print(f"UI元素总数: {len(ui_result['elements'])}")
    
    # 统计可交互元素
    clickable_count = sum(1 for e in ui_result['elements'] if e.get('clickable', False))
    text_elements_count = sum(1 for e in ui_result['elements'] if e.get('text') and e['text'].strip())
    
    print(f"可点击元素数量: {clickable_count}")
    print(f"包含文本的元素数量: {text_elements_count}")
    
    # 显示文件路径
    print("\n分析结果已保存到以下文件:")
    print(f"1. UI XML文件: {xml_path}")
    print(f"2. 完整分析结果(JSON): {json_path}")
    print(f"3. UI分析摘要: {summary_path}")
    
    # 询问是否显示摘要内容
    try:
        show_summary = input("\n是否显示UI分析摘要？(y/n): ").lower() == 'y'
        if show_summary:
            with open(summary_path, "r", encoding="utf-8") as f:
                print("\n" + f.read())
    except KeyboardInterrupt:
        pass


def main():
    """主函数"""
    test_analyze_ui()


if __name__ == "__main__":
    main() 