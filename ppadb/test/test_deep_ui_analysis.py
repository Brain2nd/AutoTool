#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试深度分析应用UI结构功能 - 测试递归元素获取
"""

import os
import sys
import pathlib
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def print_element_tree(elements: List[Dict[str, Any]], index: int = 0, depth: int = 0):
    """
    打印元素树状结构
    
    Args:
        elements: 元素列表
        index: 当前元素索引
        depth: 当前深度
    """
    if index >= len(elements):
        return
    
    element = elements[index]
    indent = "  " * depth
    
    # 获取元素的基本信息
    element_class = element.get('class', 'Unknown')
    element_text = element.get('text', '')
    element_desc = element.get('content-desc', '')
    element_id = element.get('resource-id', '')
    
    # 显示信息
    display_text = element_text or element_desc or element_id or "无文本"
    if len(display_text) > 30:
        display_text = display_text[:27] + "..."
    
    # 显示是否可点击
    clickable = "可点击" if element.get('clickable', False) else ""
    
    print(f"{indent}├─ [{element_class}] {display_text} {clickable}")
    
    # 递归显示子元素
    child_indices = element.get('child_indices', [])
    for child_index in child_indices:
        print_element_tree(elements, child_index, depth + 1)


def analyze_ui_hierarchy(ui_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析UI层次结构，统计相关信息
    
    Args:
        ui_result: UI分析结果
        
    Returns:
        分析统计信息
    """
    elements = ui_result.get('elements', [])
    
    stats = {
        'total_elements': len(elements),
        'max_depth': 0,
        'depth_counts': {},
        'clickable_elements': 0,
        'clickable_by_depth': {},
        'leaf_elements': 0,  # 没有子元素的节点
        'branch_elements': 0,  # 有子元素的节点
        'class_counts': {},
    }
    
    # 分析元素
    for element in elements:
        depth = element.get('depth', 0)
        is_clickable = element.get('clickable', False)
        has_children = len(element.get('child_indices', [])) > 0
        element_class = element.get('class', 'Unknown')
        
        # 更新最大深度
        if depth > stats['max_depth']:
            stats['max_depth'] = depth
        
        # 更新深度计数
        stats['depth_counts'][depth] = stats['depth_counts'].get(depth, 0) + 1
        
        # 更新可点击元素计数
        if is_clickable:
            stats['clickable_elements'] += 1
            stats['clickable_by_depth'][depth] = stats['clickable_by_depth'].get(depth, 0) + 1
        
        # 更新叶节点/分支节点计数
        if has_children:
            stats['branch_elements'] += 1
        else:
            stats['leaf_elements'] += 1
        
        # 更新类计数
        stats['class_counts'][element_class] = stats['class_counts'].get(element_class, 0) + 1
    
    return stats


def test_deep_ui_analysis():
    """测试深度分析应用UI结构功能"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法进行测试")
        return
    
    # 创建输出目录
    output_dir = current_dir / "deep_ui_analysis"
    output_dir.mkdir(exist_ok=True)
    
    # 准备获取当前页面UI
    print("\n===== 深度分析当前界面UI结构 =====\n")
    print("请确保您的设备屏幕上已经打开了要分析的应用")
    print("此测试将分析UI层次结构，包括深层嵌套的元素")
    
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
    
    # 分析UI层次结构
    stats = analyze_ui_hierarchy(ui_result)
    
    # 保存统计结果
    stats_path = output_dir / f"ui_stats_{timestamp}.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # 显示基本结果
    print(f"\n分析成功: {ui_result['message']}")
    print(f"应用包名: {ui_result['package_name']}")
    print(f"活动名称: {ui_result['activity_name']}")
    
    # 显示层次结构统计
    print("\n===== UI层次结构统计 =====")
    print(f"总元素数量: {stats['total_elements']}")
    print(f"最大嵌套深度: {stats['max_depth']}")
    print(f"可点击元素数量: {stats['clickable_elements']}")
    print(f"叶元素数量: {stats['leaf_elements']}")
    print(f"分支元素数量: {stats['branch_elements']}")
    
    # 分析并显示列表结构
    print("\n===== 识别列表结构 =====")
    # 使用PPADB工具类中的列表识别功能
    lists_result = adb_tool.identify_list_structures(
        ui_result=ui_result,
        similarity_threshold=0.7,
        min_items=2
    )
    
    # 如果第一次识别失败，尝试降低阈值
    if not lists_result['success'] or lists_result['list_count'] == 0:
        lists_result = adb_tool.identify_list_structures(
            ui_result=ui_result,
            similarity_threshold=0.6,
            min_items=2
        )
    
    # 保存列表分析结果
    lists_path = output_dir / f"ui_lists_{timestamp}.json"
    with open(lists_path, "w", encoding="utf-8") as f:
        json.dump(lists_result, f, ensure_ascii=False, indent=2)
        
    if not lists_result['success'] or lists_result['list_count'] == 0:
        print("未识别到列表结构")
    else:
        print(f"识别到 {lists_result['list_count']} 个非重复列表结构:")
        
        for i, list_info in enumerate(lists_result['lists']):
            root_class = list_info['root_element'].get('class', 'Unknown')
            item_class = list_info['item_class']
            item_count = list_info['item_count']
            is_nested = "（嵌套列表）" if list_info['is_nested'] else ""
            depth = list_info['depth']
            has_children = f"，包含 {len(list_info.get('child_list_indices', []))} 个子列表" if list_info.get('child_list_indices', []) else ""
            
            print(f"{i+1}. [{root_class}] - 包含 {item_count} 个 [{item_class}] 项 {is_nested}{has_children}")
            if is_nested:
                print(f"   嵌套深度: {depth}")
            
            # 显示一部分列表项示例
            print("   列表项示例:")
            for j, item_idx in enumerate(list_info['item_indices'][:3]):  # 最多显示3个
                item = ui_result['elements'][item_idx]
                item_text = item.get('text', '') or item.get('content-desc', '') or "无文本"
                if len(item_text) > 30:
                    item_text = item_text[:27] + "..."
                print(f"   - 项 {j+1}: {item_text}")
                
            if len(list_info['item_indices']) > 3:
                print(f"   ... 还有 {len(list_info['item_indices']) - 3} 个项未显示")
                
        print(f"\n列表结构分析结果已保存到: {lists_path}")
    
    # 显示文件路径
    print("\n分析结果已保存到以下文件:")
    print(f"1. UI XML文件: {xml_path}")
    print(f"2. 完整分析结果(JSON): {json_path}")
    print(f"3. 统计数据: {stats_path}")
    print(f"4. 列表结构分析: {lists_path}")
    
    # 添加列表交互功能
    while True:
        if lists_result['success'] and lists_result['list_count'] > 0:
            try:
                view_list = input("\n是否查看列表详情? (y/n): ").lower()
                if view_list == 'n':
                    break
                elif view_list == 'y':
                    list_choice = input(f"请输入要查看的列表编号 (1-{lists_result['list_count']}，0=返回): ")
                    
                    try:
                        list_idx = int(list_choice) - 1
                        if list_choice == '0':
                            continue
                        elif 0 <= list_idx < len(lists_result['lists']):
                            selected_list = lists_result['lists'][list_idx]
                            
                            print(f"\n===== 列表 {list_idx+1} 详情 =====")
                            root_element = selected_list['root_element']
                            print(f"根元素类名: {root_element.get('class', 'Unknown')}")
                            print(f"根元素深度: {root_element.get('depth', 0)}")
                            
                            if root_element.get('resource-id'):
                                print(f"根元素资源ID: {root_element.get('resource-id')}")
                                
                            bounds = root_element.get('bounds', [])
                            if bounds and len(bounds) == 4:
                                x1, y1, x2, y2 = bounds
                                width = x2 - x1
                                height = y2 - y1
                                print(f"根元素位置: {bounds}")
                                print(f"根元素尺寸: 宽度={width}, 高度={height}")
                            
                            # 显示列表项
                            item_count = selected_list['item_count']
                            print(f"\n列表共有 {item_count} 个项:")
                            
                            # 询问是否查看所有列表项
                            view_all = input("是否查看所有列表项? (y/n，默认显示前5个): ").lower()
                            
                            # 确定显示多少个列表项
                            if view_all == 'y':
                                show_count = item_count
                            else:
                                show_count = min(5, item_count)
                                
                            # 显示列表项详情
                            for i, item_idx in enumerate(selected_list['item_indices'][:show_count]):
                                item = ui_result['elements'][item_idx]
                                print(f"\n项 {i+1}:")
                                print(f"- 类名: {item.get('class', 'Unknown')}")
                                
                                text = item.get('text', '')
                                desc = item.get('content-desc', '')
                                res_id = item.get('resource-id', '')
                                
                                if text:
                                    print(f"- 文本: {text}")
                                if desc:
                                    print(f"- 描述: {desc}")
                                if res_id:
                                    print(f"- 资源ID: {res_id}")
                                    
                                # 显示元素是否可交互
                                clickable = "可点击" if item.get('clickable', False) else "不可点击"
                                print(f"- 可交互性: {clickable}")
                                
                                # 显示子元素数量
                                child_count = len(item.get('child_indices', []))
                                if child_count > 0:
                                    print(f"- 包含 {child_count} 个子元素")
                            
                            if item_count > show_count:
                                print(f"\n... 还有 {item_count - show_count} 个项未显示")
                                
                            # 如果是嵌套列表，显示父列表信息
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
        else:
            break

    # 询问是否查看元素树
    while True:
        try:
            show_tree = input("\n是否查看元素树? (y/n): ").lower()
            if show_tree == 'n':
                break
            elif show_tree == 'y':
                # 限制树的显示深度，避免输出过多
                max_depth = input("请输入要显示的最大深度（0=仅根节点，留空=全部）: ")
                try:
                    max_depth = int(max_depth) if max_depth.strip() else float('inf')
                except ValueError:
                    max_depth = float('inf')
                
                print("\n===== 元素树结构 =====")
                # 查找根元素（没有父元素的元素）
                root_indices = [i for i, el in enumerate(ui_result['elements']) 
                               if el.get('parent_index') is None]
                
                # 最多显示5个根元素及其子树
                for i, root_idx in enumerate(root_indices[:5]):
                    print(f"\n根元素 {i+1}:")
                    print_element_tree(ui_result['elements'], root_idx, 0)
                
                if len(root_indices) > 5:
                    print(f"\n... 还有 {len(root_indices) - 5} 个根元素未显示 ...")
                
                break
            else:
                print("无效输入，请输入 y 或 n")
        except KeyboardInterrupt:
            break
    
    # 询问是否搜索特定元素
    while True:
        try:
            search_option = input("\n是否搜索特定元素? (y/n): ").lower()
            if search_option == 'n':
                break
            elif search_option == 'y':
                search_text = input("请输入要搜索的文本/描述/ID: ")
                if not search_text:
                    continue
                
                # 搜索元素
                matching_elements = []
                for i, element in enumerate(ui_result['elements']):
                    text = element.get('text', '')
                    desc = element.get('content-desc', '')
                    res_id = element.get('resource-id', '')
                    
                    if (search_text.lower() in text.lower() or
                        search_text.lower() in desc.lower() or
                        search_text.lower() in res_id.lower()):
                        matching_elements.append((i, element))
                
                if not matching_elements:
                    print("未找到匹配的元素")
                    continue
                
                print(f"\n找到 {len(matching_elements)} 个匹配的元素:")
                for i, (idx, element) in enumerate(matching_elements, 1):
                    depth = element.get('depth', 0)
                    cls = element.get('class', 'Unknown')
                    text = element.get('text', '')
                    desc = element.get('content-desc', '')
                    res_id = element.get('resource-id', '')
                    display_text = text or desc or res_id or "无文本"
                    
                    print(f"{i}. [深度{depth}] [{cls}] {display_text[:50]}")
                
                # 查看选定元素的详情
                detail_choice = input("\n输入编号查看详情（0=返回）: ")
                if detail_choice == '0':
                    continue
                
                try:
                    idx = int(detail_choice) - 1
                    if 0 <= idx < len(matching_elements):
                        element_idx, element = matching_elements[idx]
                        
                        print("\n===== 元素详情 =====")
                        print(f"索引: {element_idx}")
                        print(f"深度: {element.get('depth', 0)}")
                        print(f"类名: {element.get('class', 'Unknown')}")
                        
                        if element.get('text'):
                            print(f"文本: {element.get('text')}")
                        if element.get('content-desc'):
                            print(f"描述: {element.get('content-desc')}")
                        if element.get('resource-id'):
                            print(f"资源ID: {element.get('resource-id')}")
                        
                        bounds = element.get('bounds', [])
                        if bounds:
                            x1, y1, x2, y2 = bounds
                            width = x2 - x1
                            height = y2 - y1
                            center_x = (x1 + x2) // 2
                            center_y = (y1 + y2) // 2
                            print(f"位置: {bounds}")
                            print(f"尺寸: 宽度={width}, 高度={height}")
                            print(f"中心点: ({center_x}, {center_y})")
                        
                        print("交互属性:")
                        for attr in ['clickable', 'long-clickable', 'checkable', 
                                     'checked', 'enabled', 'focusable', 
                                     'focused', 'password', 'scrollable']:
                            if attr in element:
                                print(f"- {attr}: {element[attr]}")
                        
                        # 显示父子关系
                        parent_idx = element.get('parent_index')
                        if parent_idx is not None:
                            parent = ui_result['elements'][parent_idx]
                            parent_class = parent.get('class', 'Unknown')
                            print(f"父元素: [{parent_class}] (索引 {parent_idx})")
                        
                        child_indices = element.get('child_indices', [])
                        if child_indices:
                            print(f"子元素数量: {len(child_indices)}")
                            print("子元素列表:")
                            for i, child_idx in enumerate(child_indices[:5]):  # 显示前5个
                                child = ui_result['elements'][child_idx]
                                child_class = child.get('class', 'Unknown')
                                child_text = child.get('text', '') or child.get('content-desc', '') or "无文本"
                                print(f"  {i+1}. [{child_class}] {child_text[:30]}")
                            
                            if len(child_indices) > 5:
                                print(f"  ... 还有 {len(child_indices) - 5} 个子元素未显示 ...")
                    else:
                        print("无效的编号")
                except ValueError:
                    print("无效的输入")
                except Exception as e:
                    print(f"处理元素详情时出错: {e}")
                    
            else:
                print("无效输入，请输入 y 或 n")
        except KeyboardInterrupt:
            break
    
    print("\n测试完成")


def main():
    """主函数"""
    test_deep_ui_analysis()


if __name__ == "__main__":
    main() 