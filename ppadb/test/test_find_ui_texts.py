#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试查找UI中的所有文本元素
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


def display_text_element_info(element: Dict[str, Any], index: int) -> None:
    """
    显示文本元素的详细信息
    
    Args:
        element: 元素字典
        index: 元素索引
    """
    print(f"\n----- 文本元素 #{index} -----")
    print(f"类名: {element.get('class', 'N/A')}")
    print(f"文本: {element.get('text', '')}")
    
    if 'content-desc' in element and element['content-desc']:
        print(f"描述: {element['content-desc']}")
    
    if 'resource-id' in element and element['resource-id']:
        print(f"资源ID: {element['resource-id']}")
    
    if 'bounds' in element and element['bounds']:
        bounds = element['bounds']
        x1, y1, x2, y2 = bounds
        width = x2 - x1
        height = y2 - y1
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        print(f"位置: {bounds}")
        print(f"尺寸: 宽度={width}, 高度={height}")
        print(f"中心点: ({center_x}, {center_y})")
    
    print("主要属性:")
    for attr in ['clickable', 'scrollable', 'enabled', 'focusable']:
        if attr in element:
            print(f"- {attr}: {element[attr]}")


def find_all_text_elements(include_empty: bool = False, include_content_desc: bool = True) -> Dict[str, Any]:
    """
    查找当前UI中的所有文本元素
    
    Args:
        include_empty: 是否包含空文本的元素
        include_content_desc: 是否将content-desc也视为文本
        
    Returns:
        包含文本元素列表的结果字典
    """
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        return {
            'success': False,
            'message': '未连接设备',
            'elements': [],
            'count': 0
        }
    
    # 获取当前UI结构
    ui_info = adb_tool.get_current_app_ui(pretty_print=False)
    if not ui_info['success']:
        return {
            'success': False,
            'message': f'获取UI结构失败: {ui_info["message"]}',
            'elements': [],
            'count': 0
        }
    
    # 查找所有包含文本的元素
    text_elements = []
    
    for element in ui_info['elements']:
        # 检查元素是否有文本
        has_text = False
        text_value = element.get('text', '')
        
        if text_value:
            has_text = True
        elif include_empty and 'text' in element:
            # 如果允许空文本且元素有text属性
            has_text = True
        
        # 如果设置了包含content-desc，则也检查该属性
        if not has_text and include_content_desc:
            content_desc = element.get('content-desc', '')
            if content_desc:
                has_text = True
                if not text_value:  # 如果没有text但有content-desc，则使用content-desc作为显示文本
                    element['display_text'] = content_desc
        
        # 如果元素有文本，添加到列表
        if has_text:
            if 'display_text' not in element:
                element['display_text'] = text_value
            text_elements.append(element)
    
    # 返回结果
    return {
        'success': True,
        'message': f'找到 {len(text_elements)} 个文本元素',
        'elements': text_elements,
        'count': len(text_elements)
    }


def main():
    """主函数"""
    print("正在查找当前UI中的所有文本元素...")
    
    # 是否包含空文本
    include_empty = input("是否包含空文本元素? (y/n，默认n): ").lower() == 'y'
    
    # 是否包含content-desc作为文本
    include_content_desc = input("是否将content-desc视为文本? (y/n，默认y): ")
    include_content_desc = False if include_content_desc.lower() == 'n' else True
    
    # 执行查找
    result = find_all_text_elements(include_empty, include_content_desc)
    
    if not result['success']:
        print(f"查找失败: {result['message']}")
        return
    
    if result['count'] == 0:
        print("未找到文本元素")
        return
    
    # 显示文本元素列表
    print(f"\n找到 {result['count']} 个文本元素:")
    
    # 先显示简略信息
    for i, element in enumerate(result['elements'], 1):
        class_name = element.get('class', 'Unknown')
        display_text = element.get('display_text', '')
        text_source = '文本' if display_text == element.get('text', '') else '描述'
        
        # 截断过长的文本
        if len(display_text) > 50:
            display_text = display_text[:47] + "..."
        
        print(f"{i}. [{class_name}] ({text_source}) {display_text}")
    
    # 查看元素详情
    while True:
        print("\n选项:")
        print("1. 查看元素详情")
        print("2. 显示所有文本")
        print("0. 退出")
        
        choice = input("\n请选择操作 (0-2): ")
        
        if choice == "0":
            break
        
        elif choice == "1":
            # 查看元素详情
            detail_choice = input("\n输入编号查看元素详情，或输入0返回: ")
            
            if detail_choice == "0":
                continue
            
            try:
                idx = int(detail_choice) - 1
                if 0 <= idx < len(result['elements']):
                    display_text_element_info(result['elements'][idx], idx + 1)
                else:
                    print("无效的编号")
            except ValueError:
                print("无效的输入")
        
        elif choice == "2":
            # 显示所有文本
            print("\n----- 所有文本内容 -----")
            for i, element in enumerate(result['elements'], 1):
                display_text = element.get('display_text', '')
                text_source = '文本' if display_text == element.get('text', '') else '描述'
                class_name = element.get('class', 'Unknown')
                
                print(f"{i}. [{class_name}] ({text_source}): {display_text}")
        
        else:
            print("无效的选择")


if __name__ == "__main__":
    main() 