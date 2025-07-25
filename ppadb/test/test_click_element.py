#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试元素点击功能
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


def find_clickable_elements(ui_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    查找可点击的元素
    
    Args:
        ui_result: UI分析结果
        
    Returns:
        可点击元素列表
    """
    clickable_elements = []
    
    for element in ui_result['elements']:
        if element.get('clickable', False):
            # 只添加有文本或描述或资源ID的元素，以便识别
            text = element.get('text', '')
            desc = element.get('content-desc', '')
            res_id = element.get('resource-id', '')
            
            if text or desc or res_id:
                clickable_elements.append(element)
    
    return clickable_elements


def test_click_element():
    """测试元素点击功能"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法进行测试")
        return
    
    # 显示菜单
    while True:
        print("\n===== 元素点击测试 =====")
        print("1. 获取当前界面可点击元素")
        print("2. 使用元素索引点击")
        print("3. 通过文本内容点击")
        print("4. 通过资源ID点击")
        print("5. 通过坐标点击")
        print("0. 退出")
        
        choice = input("\n请选择操作 (0-5): ")
        
        if choice == "0":
            break
        
        elif choice == "1":
            # 获取当前界面可点击元素
            print("\n正在分析当前界面...")
            ui_result = adb_tool.get_current_app_ui(pretty_print=False)
            
            if not ui_result['success']:
                print(f"获取UI结构失败: {ui_result['message']}")
                continue
            
            # 获取可点击元素
            clickable_elements = find_clickable_elements(ui_result)
            
            if not clickable_elements:
                print("未找到可点击元素")
                continue
            
            print(f"\n找到 {len(clickable_elements)} 个可点击元素:")
            
            for i, element in enumerate(clickable_elements, 1):
                text = element.get('text', '')
                desc = element.get('content-desc', '')
                res_id = element.get('resource-id', '')
                cls = element.get('class', '')
                
                # 显示标识信息
                identifier = text or desc or res_id or f"元素{i}"
                print(f"{i}. [{cls}] {identifier}")
            
            # 查看元素详情
            while True:
                detail_choice = input("\n输入编号查看元素详情，或输入0返回: ")
                
                if detail_choice == "0":
                    break
                
                try:
                    idx = int(detail_choice) - 1
                    if 0 <= idx < len(clickable_elements):
                        display_element_info(clickable_elements[idx])
                    else:
                        print("无效的编号")
                except ValueError:
                    print("无效的输入")
        
        elif choice == "2":
            # 使用元素索引点击
            print("\n正在分析当前界面...")
            ui_result = adb_tool.get_current_app_ui(pretty_print=False)
            
            if not ui_result['success']:
                print(f"获取UI结构失败: {ui_result['message']}")
                continue
            
            # 获取可点击元素
            clickable_elements = find_clickable_elements(ui_result)
            
            if not clickable_elements:
                print("未找到可点击元素")
                continue
            
            print(f"\n找到 {len(clickable_elements)} 个可点击元素:")
            
            # 映射可点击元素索引到全局元素索引
            element_indices = []
            
            for i, element in enumerate(clickable_elements, 1):
                # 找到元素在原始列表中的索引
                element_index = ui_result['elements'].index(element)
                element_indices.append(element_index)
                
                text = element.get('text', '')
                desc = element.get('content-desc', '')
                res_id = element.get('resource-id', '')
                cls = element.get('class', '')
                
                # 显示标识信息
                identifier = text or desc or res_id or f"元素{i}"
                print(f"{i}. [{cls}] {identifier} (索引: {element_index})")
            
            # 选择要点击的元素
            click_choice = input("\n输入编号选择要点击的元素，或输入0返回: ")
            
            if click_choice == "0":
                continue
            
            try:
                idx = int(click_choice) - 1
                if 0 <= idx < len(element_indices):
                    element_index = element_indices[idx]
                    
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
                    result = adb_tool.click_element(element_index, ct)
                    
                    if result['success']:
                        print(f"点击成功: {result['message']}")
                        print(f"点击位置: {result['click_position']}")
                    else:
                        print(f"点击失败: {result['message']}")
                else:
                    print("无效的编号")
            except ValueError:
                print("无效的输入")
        
        elif choice == "3":
            # 通过文本内容点击
            text = input("\n请输入要查找的文本内容: ")
            
            if not text:
                print("文本不能为空")
                continue
            
            partial_match = input("是否允许部分匹配? (y/n): ").lower() == 'y'
            
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
            print(f"\n正在查找并{ct}文本 '{text}' 的元素...")
            result = adb_tool.click_by_text(text, partial_match, ct)
            
            if result['success']:
                print(f"点击成功: {result['message']}")
                print(f"点击位置: {result['click_position']}")
                
                if result['matched_element']:
                    print("\n匹配到的元素:")
                    display_element_info(result['matched_element'])
            else:
                print(f"点击失败: {result['message']}")
        
        elif choice == "4":
            # 通过资源ID点击
            resource_id = input("\n请输入要查找的资源ID: ")
            
            if not resource_id:
                print("资源ID不能为空")
                continue
            
            partial_match = input("是否允许部分匹配? (y/n): ").lower() == 'y'
            
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
            print(f"\n正在查找并{ct}资源ID '{resource_id}' 的元素...")
            result = adb_tool.click_by_resource_id(resource_id, partial_match, ct)
            
            if result['success']:
                print(f"点击成功: {result['message']}")
                print(f"点击位置: {result['click_position']}")
                
                if result['matched_element']:
                    print("\n匹配到的元素:")
                    display_element_info(result['matched_element'])
            else:
                print(f"点击失败: {result['message']}")
        
        elif choice == "5":
            # 通过坐标点击
            try:
                x = int(input("\n请输入X坐标: "))
                y = int(input("请输入Y坐标: "))
                
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
                
                # 点击坐标
                print(f"\n正在{ct}坐标 ({x}, {y})...")
                result = adb_tool.click_by_position(x, y, ct)
                
                if result['success']:
                    print(f"点击成功: {result['message']}")
                else:
                    print(f"点击失败: {result['message']}")
            except ValueError:
                print("坐标必须是整数")
        
        else:
            print("无效的选择")


def main():
    """主函数"""
    test_click_element()


if __name__ == "__main__":
    main() 