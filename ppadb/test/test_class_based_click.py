#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试基于类名查找和点击元素的功能
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


def display_element_info(element: Dict[str, Any]) -> None:
    """
    显示元素的详细信息
    
    Args:
        element: 元素字典
    """
    print("\n----- 元素信息 -----")
    print(f"类名: {element.get('class', 'N/A')}")
    
    if 'text' in element and element['text']:
        print(f"文本: {element['text']}")
    
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
    
    print("属性:")
    for attr in ['clickable', 'long-clickable', 'checkable', 'checked', 
               'enabled', 'focusable', 'focused', 'scrollable']:
        if attr in element:
            print(f"- {attr}: {element[attr]}")


def test_class_based_search():
    """测试基于类名的元素查找和点击功能"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法进行测试")
        return
    
    # 显示菜单
    while True:
        print("\n===== 基于类名的元素查找和点击 =====")
        print("1. 查找特定类名的元素")
        print("2. 查找特定类名和文本的元素")
        print("3. 点击特定类名的元素")
        print("4. 点击特定类名和文本的元素")
        print("0. 退出")
        
        choice = input("\n请选择操作 (0-4): ")
        
        if choice == "0":
            break
        
        elif choice == "1":
            # 查找特定类名的元素
            class_name = input("\n请输入要查找的类名(例如android.view.ViewGroup): ")
            if not class_name:
                print("类名不能为空")
                continue
            
            # 查找元素
            print(f"\n正在查找类名为 '{class_name}' 的元素...")
            result = adb_tool.find_elements_by_class(class_name)
            
            if not result['success']:
                print(f"查找失败: {result['message']}")
                continue
                
            if result['count'] == 0:
                print(f"未找到类名为 '{class_name}' 的元素")
                continue
            
            print(f"\n找到 {result['count']} 个匹配元素:")
            
            for i, element in enumerate(result['elements'], 1):
                text = element.get('text', '')
                desc = element.get('content-desc', '')
                res_id = element.get('resource-id', '')
                
                # 显示标识信息
                identifier = text or desc or res_id or f"元素{i}"
                print(f"{i}. [{class_name}] {identifier}")
            
            # 查看元素详情
            while True:
                detail_choice = input("\n输入编号查看元素详情，或输入0返回: ")
                
                if detail_choice == "0":
                    break
                
                try:
                    idx = int(detail_choice) - 1
                    if 0 <= idx < len(result['elements']):
                        display_element_info(result['elements'][idx])
                    else:
                        print("无效的编号")
                except ValueError:
                    print("无效的输入")
        
        elif choice == "2":
            # 查找特定类名和文本的元素
            class_name = input("\n请输入要查找的类名(例如android.view.ViewGroup): ")
            if not class_name:
                print("类名不能为空")
                continue
                
            text = input("请输入要查找的文本内容(可选): ")
            if not text:
                text = None
                
            partial_match = input("是否允许部分匹配? (y/n): ").lower() == 'y'
            
            # 查找元素
            print(f"\n正在查找类名为 '{class_name}' 的元素", end="")
            if text:
                print(f"，且包含文本 '{text}'...", end="")
            print()
            
            result = adb_tool.find_elements_by_class(class_name, text, partial_match)
            
            if not result['success']:
                print(f"查找失败: {result['message']}")
                continue
                
            if result['count'] == 0:
                print(result['message'])
                continue
            
            print(f"\n找到 {result['count']} 个匹配元素:")
            
            for i, element in enumerate(result['elements'], 1):
                text = element.get('text', '')
                desc = element.get('content-desc', '')
                res_id = element.get('resource-id', '')
                
                # 显示标识信息
                identifier = text or desc or res_id or f"元素{i}"
                print(f"{i}. [{class_name}] {identifier}")
            
            # 查看元素详情
            while True:
                detail_choice = input("\n输入编号查看元素详情，或输入0返回: ")
                
                if detail_choice == "0":
                    break
                
                try:
                    idx = int(detail_choice) - 1
                    if 0 <= idx < len(result['elements']):
                        display_element_info(result['elements'][idx])
                    else:
                        print("无效的编号")
                except ValueError:
                    print("无效的输入")
        
        elif choice == "3":
            # 点击特定类名的元素
            class_name = input("\n请输入要查找的类名(例如android.view.ViewGroup): ")
            if not class_name:
                print("类名不能为空")
                continue
            
            # 先查找元素
            print(f"\n正在查找类名为 '{class_name}' 的元素...")
            search_result = adb_tool.find_elements_by_class(class_name)
            
            if not search_result['success']:
                print(f"查找失败: {search_result['message']}")
                continue
                
            if search_result['count'] == 0:
                print(search_result['message'])
                continue
            
            print(f"\n找到 {search_result['count']} 个匹配元素:")
            
            for i, element in enumerate(search_result['elements'], 1):
                text = element.get('text', '')
                desc = element.get('content-desc', '')
                res_id = element.get('resource-id', '')
                
                # 显示标识信息
                identifier = text or desc or res_id or f"元素{i}"
                print(f"{i}. [{class_name}] {identifier}")
            
            # 选择要点击的元素
            element_index = input(f"\n请输入要点击的元素编号(1-{search_result['count']}): ")
            try:
                idx = int(element_index) - 1
                if not (0 <= idx < search_result['count']):
                    print("无效的编号")
                    continue
            except ValueError:
                print("无效的输入")
                continue
            
            # 选择点击类型
            click_type = input("点击类型 (1=单击, 2=长按, 3=双击): ")
            
            if click_type == "1":
                ct = "click"
            elif click_type == "2":
                ct = "long_click"
            elif click_type == "3":
                ct = "double_click"
            else:
                ct = "click"  # 默认单击
            
            # 点击元素
            print(f"\n正在{ct}元素...")
            click_result = adb_tool.click_by_class(class_name, index=idx, click_type=ct)
            
            if click_result['success']:
                print(f"点击成功: {click_result['message']}")
                print(f"点击位置: {click_result['click_position']}")
            else:
                print(f"点击失败: {click_result['message']}")
        
        elif choice == "4":
            # 点击特定类名和文本的元素
            class_name = input("\n请输入要查找的类名(例如android.view.ViewGroup): ")
            if not class_name:
                print("类名不能为空")
                continue
                
            text = input("请输入要查找的文本内容(可选): ")
            if not text:
                text = None
                
            partial_match = input("是否允许部分匹配? (y/n): ").lower() == 'y'
            
            # 先查找元素
            print(f"\n正在查找类名为 '{class_name}' 的元素", end="")
            if text:
                print(f"，且包含文本 '{text}'...", end="")
            print()
            
            search_result = adb_tool.find_elements_by_class(class_name, text, partial_match)
            
            if not search_result['success']:
                print(f"查找失败: {search_result['message']}")
                continue
                
            if search_result['count'] == 0:
                print(search_result['message'])
                continue
            
            print(f"\n找到 {search_result['count']} 个匹配元素:")
            
            for i, element in enumerate(search_result['elements'], 1):
                display_text = element.get('text', '')
                desc = element.get('content-desc', '')
                res_id = element.get('resource-id', '')
                
                # 显示标识信息
                identifier = display_text or desc or res_id or f"元素{i}"
                print(f"{i}. [{class_name}] {identifier}")
            
            # 选择要点击的元素
            if search_result['count'] > 1:
                element_index = input(f"\n请输入要点击的元素编号(1-{search_result['count']}): ")
                try:
                    idx = int(element_index) - 1
                    if not (0 <= idx < search_result['count']):
                        print("无效的编号")
                        continue
                except ValueError:
                    print("无效的输入")
                    continue
            else:
                idx = 0
                print("\n只找到一个匹配元素，将点击该元素")
            
            # 选择点击类型
            click_type = input("点击类型 (1=单击, 2=长按, 3=双击): ")
            
            if click_type == "1":
                ct = "click"
            elif click_type == "2":
                ct = "long_click"
            elif click_type == "3":
                ct = "double_click"
            else:
                ct = "click"  # 默认单击
            
            # 点击元素
            print(f"\n正在{ct}元素...")
            click_result = adb_tool.click_by_class(class_name, text, idx, partial_match, ct)
            
            if click_result['success']:
                print(f"点击成功: {click_result['message']}")
                print(f"点击位置: {click_result['click_position']}")
            else:
                print(f"点击失败: {click_result['message']}")
        
        else:
            print("无效的选择")


def main():
    """主函数"""
    test_class_based_search()


if __name__ == "__main__":
    main() 