#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI树分析和列表结构识别工具
直接使用PPADBTool的工具级功能
"""

import os
import sys
import json
import time
import pathlib
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def analyze_ui_and_list(
    output_dir: Optional[pathlib.Path] = None,
    threshold: float = 0.7,
    min_items: int = 2,
    save_files: bool = True
) -> Dict[str, Any]:
    """
    分析当前UI树和识别列表结构
    
    Args:
        output_dir: 输出目录，如果为None则使用默认的test/ui_lists目录
        threshold: 列表项相似度阈值，默认0.7
        min_items: 最小列表项数量，默认2
        save_files: 是否保存分析结果到文件，默认True
        
    Returns:
        分析结果
    """
    # 创建输出目录
    if output_dir is None:
        output_dir = current_dir / "ui_lists"
    output_dir.mkdir(exist_ok=True)
    
    # 初始化结果
    result = {
        'success': False,
        'message': '',
        'ui_result': None,
        'lists_result': None,
        'file_paths': {}
    }
    
    # 创建工具实例
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        result['message'] = "未连接设备，无法进行分析"
        return result
    
    # 生成文件名时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 步骤1: 获取UI树
    print("正在获取UI结构...")
    xml_path = output_dir / f"ui_dump_{timestamp}.xml" if save_files else None
    ui_result = adb_tool.get_current_app_ui(
        pretty_print=True,
        save_xml=save_files,
        save_path=str(xml_path) if xml_path else None
    )
    
    if not ui_result['success']:
        result['message'] = f"分析UI结构失败: {ui_result['message']}"
        return result
    
    result['ui_result'] = ui_result
    
    # 如果需要保存，则保存UI分析结果
    if save_files:
        # 只保存必要的内容，UI XML可能很大
        ui_data = ui_result.copy()
        xml_content = ui_data.pop('xml')
        ui_data['xml'] = '(XML内容已保存到单独文件)'
        
        json_path = output_dir / f"ui_analysis_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(ui_data, f, ensure_ascii=False, indent=2)
        
        result['file_paths']['ui_xml'] = str(xml_path)
        result['file_paths']['ui_json'] = str(json_path)
    
    # 步骤2: 识别列表结构
    print("正在识别列表结构...")
    
    # 尝试使用给定的阈值识别列表
    lists_result = adb_tool.identify_list_structures(
        ui_result=ui_result,
        similarity_threshold=threshold,
        min_items=min_items
    )
    
    # 如果未能识别到列表，尝试降低阈值
    if not lists_result['success'] or lists_result['list_count'] == 0:
        lower_threshold = max(0.5, threshold - 0.1)
        print(f"使用阈值 {threshold} 未识别到列表，尝试降低阈值至 {lower_threshold}")
        lists_result = adb_tool.identify_list_structures(
            ui_result=ui_result,
            similarity_threshold=lower_threshold,
            min_items=min_items
        )
    
    result['lists_result'] = lists_result
    
    # 如果需要保存，则保存列表分析结果
    if save_files and lists_result['success']:
        lists_path = output_dir / f"ui_lists_{timestamp}.json"
        with open(lists_path, "w", encoding="utf-8") as f:
            json.dump(lists_result, f, ensure_ascii=False, indent=2)
        
        result['file_paths']['lists_json'] = str(lists_path)
    
    # 最终结果
    result['success'] = ui_result['success'] and lists_result['success']
    result['message'] = f"UI分析: {ui_result['message']}; 列表识别: {lists_result['message']}"
    
    return result


def print_ui_summary(ui_result: Dict[str, Any]):
    """打印UI分析摘要"""
    if not ui_result['success']:
        print(f"UI分析失败: {ui_result['message']}")
        return
    
    print("\n===== UI分析摘要 =====")
    print(f"应用包名: {ui_result['package_name']}")
    print(f"活动名称: {ui_result['activity_name']}")
    print(f"元素总数: {len(ui_result['elements'])}")
    
    # 查找最大深度
    max_depth = 0
    clickable_count = 0
    element_classes = {}
    
    for element in ui_result['elements']:
        depth = element.get('depth', 0)
        max_depth = max(max_depth, depth)
        
        if element.get('clickable', False):
            clickable_count += 1
        
        class_name = element.get('class', 'Unknown')
        element_classes[class_name] = element_classes.get(class_name, 0) + 1
    
    print(f"最大深度: {max_depth}")
    print(f"可点击元素: {clickable_count}")
    
    # 打印最常见的元素类型(前5个)
    print("\n最常见的元素类型:")
    common_classes = sorted(element_classes.items(), key=lambda x: x[1], reverse=True)[:5]
    for cls, count in common_classes:
        print(f"  {cls}: {count}个")


def print_list_summary(lists_result: Dict[str, Any], ui_result: Dict[str, Any], max_list_items: int = 3):
    """打印列表分析摘要"""
    if not lists_result['success']:
        print(f"列表分析失败: {lists_result['message']}")
        return
    
    if lists_result['list_count'] == 0:
        print("\n未识别到列表结构")
        return
    
    print(f"\n===== 识别到 {lists_result['list_count']} 个列表 =====")
    
    for i, list_info in enumerate(lists_result['lists']):
        root_class = list_info['root_element'].get('class', 'Unknown')
        item_class = list_info['item_class']
        item_count = list_info['item_count']
        is_nested = "（嵌套列表）" if list_info['is_nested'] else ""
        depth = list_info['depth']
        has_children = f"，包含 {len(list_info.get('child_list_indices', []))} 个子列表" if list_info.get('child_list_indices', []) else ""
        
        print(f"\n列表 {i+1}: [{root_class}] - 包含 {item_count} 个 [{item_class}] 项 {is_nested}{has_children}")
        
        # 显示一部分列表项示例
        print("列表项示例:")
        for j, item_idx in enumerate(list_info['item_indices'][:max_list_items]):
            item = ui_result['elements'][item_idx]
            item_text = item.get('text', '') or item.get('content-desc', '') or "无文本"
            if len(item_text) > 30:
                item_text = item_text[:27] + "..."
            print(f"  项 {j+1}: {item_text}")
            
        if len(list_info['item_indices']) > max_list_items:
            print(f"  ... 还有 {len(list_info['item_indices']) - max_list_items} 个项未显示")
        
        # 显示父列表或子列表关系
        if list_info['is_nested'] and list_info.get('parent_list_index') is not None:
            parent_idx = list_info['parent_list_index']
            if 0 <= parent_idx < len(lists_result['lists']):
                parent_class = lists_result['lists'][parent_idx]['root_element'].get('class', 'Unknown')
                print(f"父列表: 列表{parent_idx+1} [{parent_class}]")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="分析当前UI结构并识别列表")
    parser.add_argument("--threshold", type=float, default=0.7, 
                        help="列表项相似度阈值 (0.1-1.0), 默认0.7")
    parser.add_argument("--min-items", type=int, default=2,
                        help="最小列表项数量，默认2")
    parser.add_argument("--no-save", action="store_true",
                        help="不保存分析结果到文件")
    parser.add_argument("--output", type=str, default=None,
                        help="输出目录路径")
    args = parser.parse_args()
    
    # 验证参数
    if args.threshold < 0.1 or args.threshold > 1.0:
        print(f"警告: 阈值 {args.threshold} 超出有效范围(0.1-1.0)，已设为默认值0.7")
        args.threshold = 0.7
    
    if args.min_items < 1:
        print(f"警告: 最小列表项数量 {args.min_items} 无效，已设为默认值2")
        args.min_items = 2
    
    # 创建输出目录
    output_dir = None
    if args.output:
        output_dir = pathlib.Path(args.output)
    else:
        output_dir = current_dir / "ui_lists"
    
    print("\n===== UI树分析和列表结构识别 =====")
    print("请确保设备已连接并且屏幕上显示您要分析的界面")
    
    try:
        input("按回车键开始分析...")
    except KeyboardInterrupt:
        print("\n操作已取消")
        return
    
    # 执行分析
    start_time = time.time()
    result = analyze_ui_and_list(
        output_dir=output_dir,
        threshold=args.threshold,
        min_items=args.min_items,
        save_files=not args.no_save
    )
    end_time = time.time()
    
    if not result['success']:
        print(f"\n分析失败: {result['message']}")
        return
    
    # 打印结果
    print_ui_summary(result['ui_result'])
    print_list_summary(result['lists_result'], result['ui_result'])
    
    # 显示输出文件
    if not args.no_save:
        print("\n分析结果已保存到以下文件:")
        for key, path in result['file_paths'].items():
            print(f"- {key}: {path}")
    
    print(f"\n分析完成，耗时 {end_time - start_time:.2f} 秒")
    
    # 交互式查看列表
    while True:
        lists_result = result['lists_result']
        ui_result = result['ui_result']
        
        if not lists_result['success'] or lists_result['list_count'] == 0:
            break
            
        try:
            view_detail = input("\n是否查看列表详情? (y/n): ").lower()
            if view_detail != 'y':
                break
                
            list_choice = input(f"请输入要查看的列表编号 (1-{lists_result['list_count']}，0=返回): ")
            
            try:
                if list_choice == '0':
                    continue
                    
                list_idx = int(list_choice) - 1
                if 0 <= list_idx < len(lists_result['lists']):
                    selected_list = lists_result['lists'][list_idx]
                    
                    # 显示列表详细信息
                    print(f"\n===== 列表 {list_idx+1} 详情 =====")
                    root_element = selected_list['root_element']
                    print(f"根元素类名: {root_element.get('class', 'Unknown')}")
                    print(f"根元素深度: {root_element.get('depth', 0)}")
                    print(f"列表项类型: {selected_list['item_class']}")
                    print(f"列表项数量: {selected_list['item_count']}")
                    
                    if root_element.get('resource-id'):
                        print(f"根元素资源ID: {root_element.get('resource-id')}")
                    
                    # 显示所有列表项
                    view_items = input("\n是否查看所有列表项? (y/n，默认显示前5个): ").lower()
                    max_display = len(selected_list['item_indices']) if view_items == 'y' else min(5, len(selected_list['item_indices']))
                    
                    print(f"\n列表项详情 (显示 {max_display}/{selected_list['item_count']} 项):")
                    for i, item_idx in enumerate(selected_list['item_indices'][:max_display]):
                        item = ui_result['elements'][item_idx]
                        
                        print(f"\n项 {i+1}:")
                        print(f"- 类名: {item.get('class', 'Unknown')}")
                        
                        if item.get('text'):
                            print(f"- 文本: {item.get('text')}")
                        if item.get('content-desc'):
                            print(f"- 描述: {item.get('content-desc')}")
                        if item.get('resource-id'):
                            print(f"- 资源ID: {item.get('resource-id')}")
                        
                        # 显示交互属性
                        attrs = []
                        if item.get('clickable', False):
                            attrs.append("可点击")
                        if item.get('scrollable', False):
                            attrs.append("可滚动")
                        if item.get('long-clickable', False):
                            attrs.append("可长按")
                        
                        if attrs:
                            print(f"- 交互性: {', '.join(attrs)}")
                    
                    # 显示嵌套列表关系
                    if selected_list['is_nested']:
                        parent_idx = selected_list['parent_list_index']
                        if parent_idx is not None and parent_idx < len(lists_result['lists']):
                            parent_list = lists_result['lists'][parent_idx]
                            parent_class = parent_list['root_element'].get('class', 'Unknown')
                            parent_items = parent_list['item_count']
                            print(f"\n该列表是嵌套列表，属于列表 {parent_idx+1} ({parent_class}，包含 {parent_items} 项)")
                    
                    # 显示子列表信息
                    child_list_indices = selected_list.get('child_list_indices', [])
                    if child_list_indices:
                        print(f"\n该列表包含 {len(child_list_indices)} 个子列表:")
                        for child_idx in child_list_indices:
                            if 0 <= child_idx < len(lists_result['lists']):
                                child_list = lists_result['lists'][child_idx]
                                child_class = child_list['root_element'].get('class', 'Unknown')
                                child_items = child_list['item_count']
                                print(f"- 子列表 {child_idx+1}: [{child_class}] 包含 {child_items} 个项")
                else:
                    print("无效的列表编号")
            except ValueError:
                print("请输入有效的数字")
        except KeyboardInterrupt:
            break
    
    print("\n感谢使用UI列表分析工具")


if __name__ == "__main__":
    main() 