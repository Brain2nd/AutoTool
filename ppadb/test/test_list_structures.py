#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试识别应用UI中的列表结构功能
"""

import os
import sys
import pathlib
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import argparse

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def print_list_structure(list_info: Dict[str, Any], elements: List[Dict[str, Any]], index: int, max_items: int = 3):
    """
    打印列表结构信息
    
    Args:
        list_info: 列表信息
        elements: UI元素列表
        index: 列表索引
        max_items: 最多显示的列表项数量
    """
    root_element = list_info['root_element']
    root_class = root_element.get('class', 'Unknown')
    item_class = list_info['item_class']
    item_count = list_info['item_count']
    is_nested = "（嵌套列表）" if list_info['is_nested'] else ""
    depth = list_info['depth']
    
    # 显示标题
    print(f"\n=== 列表 {index+1} ===")
    print(f"根元素: [{root_class}]")
    print(f"列表项类型: [{item_class}]")
    print(f"列表项数量: {item_count} {is_nested}")
    
    if is_nested:
        print(f"嵌套深度: {depth}")
    
    # 显示子列表信息
    child_list_indices = list_info.get('child_list_indices', [])
    if child_list_indices:
        print(f"包含 {len(child_list_indices)} 个子列表")
    
    # 显示根元素信息
    resource_id = root_element.get('resource-id', '')
    if resource_id:
        print(f"根元素资源ID: {resource_id}")
    
    # 显示列表项示例
    print("\n列表项示例:")
    for i, item_idx in enumerate(list_info['item_indices'][:max_items]):
        item = elements[item_idx]
        # 获取项目的文本信息
        text = item.get('text', '')
        desc = item.get('content-desc', '')
        res_id = item.get('resource-id', '')
        
        # 确定显示的文本
        display_text = text or desc or res_id or "无文本"
        if len(display_text) > 40:
            display_text = display_text[:37] + "..."
        
        # 显示是否可点击
        clickable = "可点击" if item.get('clickable', False) else ""
        
        print(f"{i+1}. {display_text} {clickable}")
    
    # 如果有更多项目，显示省略信息
    if len(list_info['item_indices']) > max_items:
        print(f"... 还有 {len(list_info['item_indices']) - max_items} 个项目未显示")


def test_list_structure_identification():
    """测试列表结构识别功能"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法进行测试")
        return
    
    # 创建输出目录
    output_dir = current_dir / "list_structures"
    output_dir.mkdir(exist_ok=True)
    
    # 准备获取当前页面UI
    print("\n===== 识别当前界面的列表结构 =====\n")
    print("请确保您的设备屏幕上已经打开了要分析的应用")
    print("此测试将分析UI中可能存在的列表结构，包括嵌套列表")
    
    try:
        input("按回车键继续...")
    except KeyboardInterrupt:
        print("\n操作已取消")
        return
    
    # 生成保存路径
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
    
    # 保存基本UI分析结果为JSON
    json_path = output_dir / f"ui_analysis_{timestamp}.json"
    
    # 不保存完整XML，它可能会很大
    xml_content = ui_result.pop('xml')
    ui_result['xml'] = '(XML内容已保存到单独文件)'
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ui_result, f, ensure_ascii=False, indent=2)
    
    # 显示基本结果
    print(f"\n分析成功: {ui_result['message']}")
    print(f"应用包名: {ui_result['package_name']}")
    print(f"活动名称: {ui_result['activity_name']}")
    
    # 识别列表结构
    print("\n正在识别列表结构...")
    lists_result = None
    
    # 尝试不同的相似度阈值
    for threshold in [0.8, 0.7, 0.6]:
        print(f"尝试相似度阈值: {threshold}")
        lists_result = adb_tool.identify_list_structures(
            ui_result=ui_result,
            similarity_threshold=threshold,
            min_items=2
        )
        
        if lists_result['success'] and lists_result['list_count'] > 0:
            print(f"使用阈值 {threshold} 识别到 {lists_result['list_count']} 个列表")
            break
        else:
            print(f"使用阈值 {threshold} 未识别到列表")
    
    # 保存列表分析结果
    lists_path = output_dir / f"ui_lists_{timestamp}.json"
    with open(lists_path, "w", encoding="utf-8") as f:
        json.dump(lists_result, f, ensure_ascii=False, indent=2)
    
    # 显示列表分析结果
    if not lists_result['success'] or lists_result['list_count'] == 0:
        print("\n未识别到列表结构")
        print("可能原因:")
        print("1. 当前界面不包含列表")
        print("2. 列表结构不规则，相似度不足")
        print("3. 列表项数量太少")
        print("\n可以尝试调整参数重新识别")
    else:
        print(f"\n成功识别出 {lists_result['list_count']} 个非重复列表结构:")
        
        # 显示列表概要
        for i, list_info in enumerate(lists_result['lists']):
            root_class = list_info['root_element'].get('class', 'Unknown')
            item_class = list_info['item_class']
            item_count = list_info['item_count']
            is_nested = "（嵌套列表）" if list_info['is_nested'] else ""
            has_children = f"，包含 {len(list_info.get('child_list_indices', []))} 个子列表" if list_info.get('child_list_indices', []) else ""
            
            print(f"{i+1}. [{root_class}] - 包含 {item_count} 个 [{item_class}] 项 {is_nested}{has_children}")
        
        # 显示文件路径
        print(f"\n分析结果已保存到: {lists_path}")
        
        # 交互式查看列表
        while True:
            try:
                view_detail = input("\n是否查看列表详情? (y/n): ").lower()
                if view_detail == 'n':
                    break
                elif view_detail == 'y':
                    list_choice = input(f"请输入要查看的列表编号 (1-{lists_result['list_count']}，0=返回): ")
                    
                    try:
                        if list_choice == '0':
                            continue
                            
                        list_idx = int(list_choice) - 1
                        if 0 <= list_idx < len(lists_result['lists']):
                            # 打印列表详情
                            print_list_structure(
                                lists_result['lists'][list_idx],
                                ui_result['elements'],
                                list_idx
                            )
                            
                            # 查看列表项详情选项
                            view_items = input("\n是否查看列表项详情? (y/n): ").lower()
                            if view_items == 'y':
                                selected_list = lists_result['lists'][list_idx]
                                max_index = len(selected_list['item_indices'])
                                
                                item_choice = input(f"请输入列表项编号 (1-{max_index}，0=返回): ")
                                try:
                                    if item_choice == '0':
                                        continue
                                        
                                    item_idx = int(item_choice) - 1
                                    if 0 <= item_idx < max_index:
                                        element_idx = selected_list['item_indices'][item_idx]
                                        element = ui_result['elements'][element_idx]
                                        
                                        print(f"\n=== 列表项 {item_idx+1} 详情 ===")
                                        print(f"类名: {element.get('class', 'Unknown')}")
                                        
                                        if element.get('text'):
                                            print(f"文本: {element.get('text')}")
                                        if element.get('content-desc'):
                                            print(f"描述: {element.get('content-desc')}")
                                        if element.get('resource-id'):
                                            print(f"资源ID: {element.get('resource-id')}")
                                        
                                        bounds = element.get('bounds', [])
                                        if bounds and len(bounds) == 4:
                                            x1, y1, x2, y2 = bounds
                                            width = x2 - x1
                                            height = y2 - y1
                                            print(f"位置: {bounds}")
                                            print(f"尺寸: 宽度={width}, 高度={height}")
                                        
                                        print("交互属性:")
                                        for attr in ['clickable', 'long-clickable', 'checkable', 
                                                   'checked', 'enabled', 'focusable', 
                                                   'focused', 'scrollable']:
                                            if attr in element and element[attr]:
                                                print(f"- {attr}: {element[attr]}")
                                        
                                        # 显示子元素
                                        child_indices = element.get('child_indices', [])
                                        if child_indices:
                                            print(f"\n包含 {len(child_indices)} 个子元素:")
                                            for j, child_idx in enumerate(child_indices[:3]):
                                                child = ui_result['elements'][child_idx]
                                                child_class = child.get('class', 'Unknown')
                                                child_text = child.get('text', '') or child.get('content-desc', '') or "无文本"
                                                if len(child_text) > 30:
                                                    child_text = child_text[:27] + "..."
                                                print(f"{j+1}. [{child_class}] {child_text}")
                                            
                                            if len(child_indices) > 3:
                                                print(f"... 还有 {len(child_indices) - 3} 个子元素未显示")
                                                
                                        # 点击测试选项
                                        click_test = input("\n是否尝试点击此元素? (y/n): ").lower()
                                        if click_test == 'y':
                                            click_result = adb_tool.click_element(element)
                                            if click_result['success']:
                                                print(f"点击成功: {click_result['message']}")
                                                print(f"点击坐标: {click_result['click_position']}")
                                                
                                                # 等待一会，然后提示是否刷新分析
                                                time.sleep(1)
                                                refresh = input("是否刷新分析当前页面? (y/n): ").lower()
                                                if refresh == 'y':
                                                    return test_list_structure_identification()
                                            else:
                                                print(f"点击失败: {click_result['message']}")
                                    else:
                                        print("无效的列表项编号")
                                except ValueError:
                                    print("请输入有效的数字")
                            
                            # 显示嵌套列表信息
                            if selected_list['is_nested']:
                                parent_idx = selected_list['parent_list_index']
                                if parent_idx is not None and parent_idx < len(lists_result['lists']):
                                    parent_list = lists_result['lists'][parent_idx]
                                    parent_class = parent_list['root_element'].get('class', 'Unknown')
                                    parent_items = parent_list['item_count']
                                    print(f"\n该列表是嵌套列表，属于列表 {parent_idx+1} ({parent_class}，包含 {parent_items} 项)")
                            
                            # 显示子列表信息（如果有）
                            child_list_indices = selected_list.get('child_list_indices', [])
                            if child_list_indices:
                                print(f"\n该列表包含 {len(child_list_indices)} 个子列表:")
                                for child_idx in child_list_indices:
                                    if 0 <= child_idx < len(lists_result['lists']):
                                        child_list = lists_result['lists'][child_idx]
                                        child_class = child_list['root_element'].get('class', 'Unknown')
                                        child_items = child_list['item_count']
                                        print(f"- 子列表 {child_idx+1}: [{child_class}] 包含 {child_items} 个 [{child_list['item_class']}] 项")
                                
                                # 询问是否查看特定子列表
                                view_child = input("\n是否查看特定子列表? (输入子列表编号，0=返回): ")
                                try:
                                    if view_child != '0':
                                        child_list_idx = int(view_child) - 1
                                        if 0 <= child_list_idx < len(lists_result['lists']):
                                            # 递归查看子列表
                                            list_idx = child_list_idx
                                            continue
                                except ValueError:
                                    pass
                        else:
                            print("无效的列表编号")
                    except ValueError:
                        print("请输入有效的数字")
                else:
                    print("无效输入，请输入 y 或 n")
            except KeyboardInterrupt:
                break
    
    # 显示文件路径
    print("\n所有分析结果已保存到以下文件:")
    print(f"1. UI XML文件: {xml_path}")
    print(f"2. UI分析结果: {json_path}")
    print(f"3. 列表结构分析: {lists_path}")
    
    print("\n测试完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="识别Android应用UI中的列表结构")
    parser.add_argument("--threshold", type=float, default=0.7, 
                        help="列表项相似度阈值，范围0.1-1.0，默认0.7")
    parser.add_argument("--min-items", type=int, default=2,
                        help="列表最少包含的项数，默认2")
    
    args = parser.parse_args()
    
    if args.threshold < 0.1 or args.threshold > 1.0:
        print(f"警告: 阈值 {args.threshold} 超出合理范围(0.1-1.0)，将使用默认值0.7")
        args.threshold = 0.7
    
    if args.min_items < 1:
        print(f"警告: 最少项数 {args.min_items} 无效，将使用默认值2")
        args.min_items = 2
    
    # 执行测试
    test_list_structure_identification()


if __name__ == "__main__":
    main() 