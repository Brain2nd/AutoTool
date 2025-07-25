#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试查找和定位UI元素功能
"""

import os
import sys
import pathlib
import json
import time
import re
from datetime import datetime

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def find_elements_by_text(elements, search_text, fuzzy=True):
    """
    通过文本内容查找元素
    
    Args:
        elements: 元素列表
        search_text: 要搜索的文本
        fuzzy: 是否模糊匹配
    
    Returns:
        匹配的元素列表
    """
    results = []
    
    for element in elements:
        text = element.get('text', '')
        desc = element.get('content-desc', '')
        
        if fuzzy:
            # 模糊匹配（包含关系）
            if search_text.lower() in text.lower() or search_text.lower() in desc.lower():
                results.append(element)
        else:
            # 精确匹配
            if search_text == text or search_text == desc:
                results.append(element)
    
    return results


def find_elements_by_resource_id(elements, resource_id, fuzzy=True):
    """
    通过资源ID查找元素
    
    Args:
        elements: 元素列表
        resource_id: 要搜索的资源ID
        fuzzy: 是否模糊匹配
    
    Returns:
        匹配的元素列表
    """
    results = []
    
    for element in elements:
        res_id = element.get('resource-id', '')
        
        if fuzzy:
            # 模糊匹配（包含关系）
            if resource_id.lower() in res_id.lower():
                results.append(element)
        else:
            # 精确匹配
            if resource_id == res_id:
                results.append(element)
    
    return results


def find_elements_by_class(elements, class_name, fuzzy=True):
    """
    通过类名查找元素
    
    Args:
        elements: 元素列表
        class_name: 要搜索的类名
        fuzzy: 是否模糊匹配
    
    Returns:
        匹配的元素列表
    """
    results = []
    
    for element in elements:
        cls = element.get('class', '')
        
        if fuzzy:
            # 模糊匹配（包含关系）
            if class_name.lower() in cls.lower():
                results.append(element)
        else:
            # 精确匹配
            if class_name == cls:
                results.append(element)
    
    return results


def print_element_details(element, index=None):
    """
    打印元素的详细信息
    
    Args:
        element: 元素字典
        index: 元素索引（可选）
    """
    header = f"元素 {index}:" if index is not None else "元素详情:"
    print(f"\n{header}")
    
    # 基本属性
    print(f"类名: {element.get('class', 'N/A')}")
    
    text = element.get('text', '')
    if text:
        print(f"文本: {text}")
    
    desc = element.get('content-desc', '')
    if desc:
        print(f"描述: {desc}")
    
    res_id = element.get('resource-id', '')
    if res_id:
        print(f"资源ID: {res_id}")
    
    # 位置信息
    bounds = element.get('bounds', [])
    if bounds:
        x1, y1, x2, y2 = bounds
        width = x2 - x1
        height = y2 - y1
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        print(f"位置: {bounds} (宽度: {width}, 高度: {height}, 中心点: [{center_x}, {center_y}])")
    
    # 交互属性
    print("交互性质:")
    print(f"- 可点击: {element.get('clickable', False)}")
    print(f"- 可长按: {element.get('long-clickable', False)}")
    print(f"- 可滚动: {element.get('scrollable', False)}")
    print(f"- 可选中: {element.get('checkable', False)}")
    print(f"- 已启用: {element.get('enabled', False)}")
    print(f"- 可获取焦点: {element.get('focusable', False)}")


def test_find_ui_element():
    """测试查找和定位UI元素功能"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法进行测试")
        return
    
    # 准备获取当前页面UI
    print("\n===== 查找和定位UI元素 =====\n")
    print("请确保您的设备屏幕上已经打开了要分析的应用")
    
    try:
        input("按回车键继续...")
    except KeyboardInterrupt:
        print("\n操作已取消")
        return
    
    # 获取UI结构
    print("正在获取UI结构...")
    ui_result = adb_tool.get_current_app_ui(pretty_print=False)
    
    if not ui_result['success']:
        print(f"获取UI结构失败: {ui_result['message']}")
        return
    
    elements = ui_result['elements']
    print(f"\n成功获取UI结构，包含 {len(elements)} 个元素")
    print(f"应用包名: {ui_result['package_name']}")
    print(f"活动名称: {ui_result['activity_name']}")
    
    # 搜索选项菜单
    while True:
        print("\n===== 元素搜索选项 =====")
        print("1. 按文本内容搜索")
        print("2. 按资源ID搜索")
        print("3. 按类名搜索")
        print("4. 显示所有可点击元素")
        print("5. 显示所有可滚动元素")
        print("0. 退出")
        
        try:
            choice = input("\n请选择搜索方式 (0-5): ")
            
            if choice == "0":
                break
            
            if choice == "1":
                # 按文本搜索
                search_text = input("请输入要搜索的文本: ")
                if not search_text:
                    continue
                
                fuzzy = input("是否使用模糊匹配? (y/n): ").lower() == 'y'
                results = find_elements_by_text(elements, search_text, fuzzy)
            
            elif choice == "2":
                # 按资源ID搜索
                resource_id = input("请输入要搜索的资源ID: ")
                if not resource_id:
                    continue
                
                fuzzy = input("是否使用模糊匹配? (y/n): ").lower() == 'y'
                results = find_elements_by_resource_id(elements, resource_id, fuzzy)
            
            elif choice == "3":
                # 按类名搜索
                class_name = input("请输入要搜索的类名: ")
                if not class_name:
                    continue
                
                fuzzy = input("是否使用模糊匹配? (y/n): ").lower() == 'y'
                results = find_elements_by_class(elements, class_name, fuzzy)
            
            elif choice == "4":
                # 显示所有可点击元素
                results = [e for e in elements if e.get('clickable', False)]
            
            elif choice == "5":
                # 显示所有可滚动元素
                results = [e for e in elements if e.get('scrollable', False)]
            
            else:
                print("无效的选择，请重新输入")
                continue
            
            # 显示搜索结果
            if not results:
                print("未找到匹配的元素")
                continue
            
            print(f"\n找到 {len(results)} 个匹配的元素:")
            
            # 显示搜索结果的简要信息
            for i, element in enumerate(results, 1):
                text = element.get('text', '')
                desc = element.get('content-desc', '')
                res_id = element.get('resource-id', '')
                cls = element.get('class', '')
                
                # 显示摘要信息
                display_text = text or desc or res_id or "无文本"
                print(f"{i}. [{cls}] - {display_text[:50]}")
            
            # 允许用户查看详情
            while True:
                detail_choice = input("\n输入元素编号查看详情，或输入0返回: ")
                
                if detail_choice == "0":
                    break
                
                try:
                    idx = int(detail_choice)
                    if 1 <= idx <= len(results):
                        print_element_details(results[idx-1], idx)
                    else:
                        print("无效的编号")
                except ValueError:
                    print("无效的输入")
        
        except KeyboardInterrupt:
            print("\n操作已取消")
            break


def main():
    """主函数"""
    test_find_ui_element()


if __name__ == "__main__":
    main() 