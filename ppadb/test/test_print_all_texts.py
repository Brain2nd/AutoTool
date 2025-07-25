#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查找并直接打印当前UI中的所有文本内容
"""

import os
import sys
import pathlib
import time
from typing import Dict, Any, List

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def print_all_texts():
    """查找并打印当前UI中的所有文本"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法获取UI文本")
        return
    
    # 获取当前UI结构
    print("正在获取当前UI结构...")
    ui_info = adb_tool.get_current_app_ui(pretty_print=False)
    
    if not ui_info['success']:
        print(f"获取UI结构失败: {ui_info['message']}")
        return
    
    # 提取所有文本
    text_elements = []
    
    for element in ui_info['elements']:
        # 获取元素文本和描述
        text = element.get('text', '')
        content_desc = element.get('content-desc', '')
        resource_id = element.get('resource-id', '')
        class_name = element.get('class', '')
        
        # 如果有text或content-desc，添加到列表
        if text or content_desc:
            text_elements.append({
                'class': class_name,
                'text': text,
                'content-desc': content_desc,
                'resource-id': resource_id,
                'bounds': element.get('bounds', []),
                'clickable': element.get('clickable', False)
            })
    
    # 打印结果
    if not text_elements:
        print("当前UI中未发现任何文本内容")
        return
    
    print(f"\n找到 {len(text_elements)} 个文本元素:")
    print("=" * 60)
    
    # 打印文本信息，按类型分类
    print("\n【文本内容】")
    for i, element in enumerate(text_elements, 1):
        if element['text']:
            print(f"{i}. [{element['class']}] {element['text']}")
    
    print("\n【描述内容】")
    for i, element in enumerate(text_elements, 1):
        if element['content-desc'] and not element['text']:
            print(f"{i}. [{element['class']}] {element['content-desc']}")
    
    # 打印可点击的文本元素
    clickable_texts = [e for e in text_elements if e['clickable']]
    if clickable_texts:
        print("\n【可点击的文本元素】")
        for i, element in enumerate(clickable_texts, 1):
            display_text = element['text'] or element['content-desc']
            print(f"{i}. [{element['class']}] {display_text}")
    
    print("=" * 60)
    
    # 获取当前应用信息
    if ui_info['package_name']:
        print(f"\n当前应用: {ui_info['package_name']}")
        print(f"当前活动: {ui_info['activity_name']}")


if __name__ == "__main__":
    print_all_texts() 