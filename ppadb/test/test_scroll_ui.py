#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试UI滚动功能
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


def test_ui_scroll():
    """测试UI滚动功能"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法进行测试")
        return
    
    # 显示菜单
    while True:
        print("\n===== UI滚动功能测试 =====")
        print("1. 查找可滚动元素")
        print("2. 滚动指定元素")
        print("3. 滚动整个屏幕")
        print("4. 自动滚动所有可滚动元素")
        print("0. 退出")
        
        choice = input("\n请选择操作 (0-4): ")
        
        if choice == "0":
            break
        
        elif choice == "1":
            # 查找可滚动元素
            print("\n正在查找当前UI中的可滚动元素...")
            result = adb_tool.find_scrollable_elements()
            
            if not result['success']:
                print(f"查找失败: {result['message']}")
                continue
                
            if result['count'] == 0:
                print(f"未找到可滚动元素")
                continue
            
            print(f"\n找到 {result['count']} 个可滚动元素:")
            
            for i, element in enumerate(result['elements'], 1):
                class_name = element.get('class', 'Unknown')
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
            # 滚动指定元素
            # 先查找可滚动元素
            print("\n正在查找当前UI中的可滚动元素...")
            result = adb_tool.find_scrollable_elements()
            
            if not result['success']:
                print(f"查找失败: {result['message']}")
                continue
                
            if result['count'] == 0:
                print(f"未找到可滚动元素")
                continue
            
            print(f"\n找到 {result['count']} 个可滚动元素:")
            
            for i, element in enumerate(result['elements'], 1):
                class_name = element.get('class', 'Unknown')
                text = element.get('text', '')
                desc = element.get('content-desc', '')
                res_id = element.get('resource-id', '')
                
                # 显示标识信息
                identifier = text or desc or res_id or f"元素{i}"
                print(f"{i}. [{class_name}] {identifier}")
            
            # 选择要滚动的元素
            element_index = input(f"\n请输入要滚动的元素编号(1-{result['count']}): ")
            try:
                idx = int(element_index) - 1
                if not (0 <= idx < result['count']):
                    print("无效的编号")
                    continue
            except ValueError:
                print("无效的输入")
                continue
            
            # 选择滚动方向
            print("\n滚动方向:")
            print("1. 向下滚动(手指向上滑)")
            print("2. 向上滚动(手指向下滑)")
            print("3. 向右滚动(手指向左滑)")
            print("4. 向左滚动(手指向右滑)")
            direction_choice = input("请选择滚动方向 (1-4): ")
            
            if direction_choice == "1":
                direction = "down"
            elif direction_choice == "2":
                direction = "up"
            elif direction_choice == "3":
                direction = "right"
            elif direction_choice == "4":
                direction = "left"
            else:
                print("无效的选择，使用默认方向(向下)")
                direction = "down"
            
            # 滚动距离
            distance_str = input("请输入滚动距离(相对于元素尺寸的比例，范围0.1-1.0，默认0.5): ")
            try:
                distance = float(distance_str)
                if distance < 0.1 or distance > 1.0:
                    print("无效的距离，使用默认值0.5")
                    distance = 0.5
            except ValueError:
                print("无效的输入，使用默认值0.5")
                distance = 0.5
            
            # 滚动持续时间
            duration_str = input("请输入滚动持续时间(毫秒，默认300ms): ")
            try:
                duration = int(duration_str)
                if duration < 50:
                    print("持续时间过短，使用默认值300ms")
                    duration = 300
            except ValueError:
                print("无效的输入，使用默认值300ms")
                duration = 300
            
            # 执行滚动
            print(f"\n正在{direction}方向滚动元素...")
            scroll_result = adb_tool.scroll_element(
                result['elements'][idx], 
                direction=direction, 
                distance=distance, 
                duration=duration
            )
            
            if scroll_result['success']:
                print(f"滚动成功: {scroll_result['message']}")
                print(f"滚动信息: 起点{scroll_result['scroll_info']['start']} -> 终点{scroll_result['scroll_info']['end']}")
            else:
                print(f"滚动失败: {scroll_result['message']}")
        
        elif choice == "3":
            # 滚动整个屏幕
            # 选择滚动方向
            print("\n滚动方向:")
            print("1. 向下滚动(手指向上滑)")
            print("2. 向上滚动(手指向下滑)")
            print("3. 向右滚动(手指向左滑)")
            print("4. 向左滚动(手指向右滑)")
            direction_choice = input("请选择滚动方向 (1-4): ")
            
            if direction_choice == "1":
                direction = "down"
            elif direction_choice == "2":
                direction = "up"
            elif direction_choice == "3":
                direction = "right"
            elif direction_choice == "4":
                direction = "left"
            else:
                print("无效的选择，使用默认方向(向下)")
                direction = "down"
            
            # 滚动距离
            distance_str = input("请输入滚动距离(相对于屏幕尺寸的比例，范围0.1-1.0，默认0.5): ")
            try:
                distance = float(distance_str)
                if distance < 0.1 or distance > 1.0:
                    print("无效的距离，使用默认值0.5")
                    distance = 0.5
            except ValueError:
                print("无效的输入，使用默认值0.5")
                distance = 0.5
            
            # 滚动持续时间
            duration_str = input("请输入滚动持续时间(毫秒，默认300ms): ")
            try:
                duration = int(duration_str)
                if duration < 50:
                    print("持续时间过短，使用默认值300ms")
                    duration = 300
            except ValueError:
                print("无效的输入，使用默认值300ms")
                duration = 300
            
            # 执行滚动
            print(f"\n正在{direction}方向滚动屏幕...")
            scroll_result = adb_tool.scroll_screen(
                direction=direction, 
                distance=distance, 
                duration=duration
            )
            
            if scroll_result['success']:
                print(f"滚动成功: {scroll_result['message']}")
                print(f"滚动信息: 起点{scroll_result['scroll_info']['start']} -> 终点{scroll_result['scroll_info']['end']}")
            else:
                print(f"滚动失败: {scroll_result['message']}")
        
        elif choice == "4":
            # 自动滚动所有可滚动元素
            # 设置最大尝试次数
            attempts_str = input("请输入每个元素的最大尝试次数(默认5次): ")
            try:
                max_attempts = int(attempts_str)
                if max_attempts <= 0:
                    print("无效的尝试次数，使用默认值5")
                    max_attempts = 5
            except ValueError:
                print("无效的输入，使用默认值5")
                max_attempts = 5
            
            # 设置等待时间
            wait_str = input("请输入每次滚动后的等待时间(秒，默认1秒): ")
            try:
                wait_time = float(wait_str)
                if wait_time < 0.1:
                    print("等待时间过短，使用默认值1秒")
                    wait_time = 1.0
            except ValueError:
                print("无效的输入，使用默认值1秒")
                wait_time = 1.0
            
            # 选择滚动方向
            print("\n请选择要尝试的滚动方向:")
            print("1. 只向下滚动")
            print("2. 只向上滚动")
            print("3. 只水平滚动(左右)")
            print("4. 上下滚动")
            print("5. 所有方向")
            directions_choice = input("请选择 (1-5，默认4): ")
            
            if directions_choice == "1":
                directions = ['down']
            elif directions_choice == "2":
                directions = ['up']
            elif directions_choice == "3":
                directions = ['left', 'right']
            elif directions_choice == "4":
                directions = ['down', 'up']
            elif directions_choice == "5":
                directions = ['down', 'up', 'left', 'right']
            else:
                print("使用默认选择(上下滚动)")
                directions = ['down', 'up']
            
            # 执行自动滚动
            print(f"\n正在开始自动滚动所有可滚动元素...")
            print(f"方向: {', '.join(directions)}, 最大尝试次数: {max_attempts}, 等待时间: {wait_time}秒")
            
            scroll_all_result = adb_tool.auto_scroll_all(
                max_attempts=max_attempts,
                directions=directions,
                wait_time=wait_time
            )
            
            if scroll_all_result['success']:
                print(f"\n{scroll_all_result['message']}")
                
                # 显示详细结果
                show_details = input("\n是否显示详细结果? (y/n): ").lower() == 'y'
                
                if show_details and scroll_all_result['scroll_results']:
                    print("\n----- 详细滚动结果 -----")
                    
                    for i, element_result in enumerate(scroll_all_result['scroll_results'], 1):
                        element_info = element_result['element_info']
                        class_name = element_info.get('class', 'Unknown')
                        identifier = (element_info.get('text', '') or 
                                     element_info.get('content-desc', '') or 
                                     element_info.get('resource-id', '') or 
                                     f"元素{i}")
                        
                        print(f"\n{i}. [{class_name}] {identifier}")
                        
                        for dir_result in element_result['directions']:
                            direction = dir_result['direction']
                            success = "成功" if dir_result['success'] else "失败"
                            attempts = dir_result['attempts']
                            
                            print(f"  - {direction} 方向: {success}, 尝试次数: {attempts}")
            else:
                print(f"自动滚动失败: {scroll_all_result['message']}")
        
        else:
            print("无效的选择")


def main():
    """主函数"""
    test_ui_scroll()


if __name__ == "__main__":
    main() 