#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI分析结果保存工具 - 可以将UI组件分析结果保存为多种格式
"""

import os
import sys
import pathlib
import time
import json
import csv
import argparse
from typing import Dict, Any, List, Optional

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def get_default_output_dir() -> str:
    """获取默认的输出目录"""
    # 直接返回当前脚本所在目录作为默认输出路径
    return str(pathlib.Path(__file__).parent)


def save_ui_analysis(output_dir: Optional[str] = None, 
                    formats: List[str] = None,
                    capture_screenshot: bool = True,
                    max_elements: int = 200) -> Dict[str, Any]:
    """
    获取UI分析结果并保存为指定格式
    
    Args:
        output_dir: 输出目录，如果不指定则使用当前脚本所在目录
        formats: 要保存的格式列表，支持 json, csv, xml，默认为 json
        capture_screenshot: 是否同时捕获并标记屏幕截图
        max_elements: 截图标记时的最大元素数量
        
    Returns:
        分析结果
    """
    # 设置默认格式
    if not formats:
        formats = ['json']
    
    # 确定输出目录
    if not output_dir:
        output_dir = get_default_output_dir()
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("❌ 未连接设备，无法分析UI")
        return {
            'success': False,
            'message': '未连接设备'
        }
    
    # 生成文件名基础（时间戳）
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    base_filename = f"ui_analysis_{timestamp}"
    
    # 获取UI结构
    print("📱 正在获取设备UI结构...")
    ui_info = adb_tool.get_current_app_ui(pretty_print=False)
    
    if not ui_info['success']:
        print(f"❌ 获取UI结构失败: {ui_info['message']}")
        return ui_info
    
    print(f"✓ 获取UI结构成功: {len(ui_info['elements'])} 个元素")
    
    # 选择性捕获并标记截图
    if capture_screenshot:
        print("📷 正在捕获屏幕并标记UI组件...")
        screenshot_path = os.path.join(output_dir, f"{base_filename}.png")
        screenshot_result = adb_tool.capture_and_mark_all_elements(
            save_path=screenshot_path,
            highlight_special=True,
            max_elements=max_elements
        )
        
        if screenshot_result['success']:
            print(f"✓ 截图保存成功: {screenshot_result['marked_screenshot']}")
        else:
            print(f"⚠️ 截图失败: {screenshot_result['message']}")
    
    # 处理元素统计数据
    print("📊 正在统计UI元素数据...")
    
    # 基本应用信息
    app_info = {
        'package_name': ui_info['package_name'],
        'activity_name': ui_info.get('activity_name', ''),
        'timestamp': timestamp,
        'datetime': time.strftime("%Y-%m-%d %H:%M:%S"),
        'total_elements': len(ui_info['elements'])
    }
    
    # 元素类型统计
    class_counts = {}
    for element in ui_info['elements']:
        if 'class' in element:
            class_name = element['class']
            class_short_name = class_name.split('.')[-1]  # 短类名（仅最后部分）
            
            if class_name not in class_counts:
                class_counts[class_name] = {
                    'count': 0,
                    'short_name': class_short_name
                }
            
            class_counts[class_name]['count'] += 1
    
    # 交互元素统计
    interaction_stats = {
        'clickable': sum(1 for e in ui_info['elements'] if e.get('clickable', False)),
        'scrollable': sum(1 for e in ui_info['elements'] if e.get('scrollable', False)),
        'long_clickable': sum(1 for e in ui_info['elements'] if e.get('long-clickable', False)),
        'focusable': sum(1 for e in ui_info['elements'] if e.get('focusable', False)),
        'enabled': sum(1 for e in ui_info['elements'] if e.get('enabled', False)),
        'checked': sum(1 for e in ui_info['elements'] if e.get('checked', False)),
        'password': sum(1 for e in ui_info['elements'] if e.get('password', False)),
    }
    
    # 深度分布统计
    depth_counts = {}
    for element in ui_info['elements']:
        depth = element.get('depth', 0)
        if depth not in depth_counts:
            depth_counts[depth] = 0
        depth_counts[depth] += 1
    
    # 文本元素分析
    text_elements = []
    for element in ui_info['elements']:
        if 'text' in element and element['text']:
            text_elements.append({
                'text': element['text'],
                'class': element.get('class', '').split('.')[-1],
                'resource-id': element.get('resource-id', ''),
                'bounds': element.get('bounds', []),
                'clickable': element.get('clickable', False),
                'element_index': ui_info['elements'].index(element)
            })
    
    # 构建完整分析结果
    analysis_result = {
        'app_info': app_info,
        'class_statistics': class_counts,
        'interaction_statistics': interaction_stats,
        'depth_distribution': depth_counts,
        'text_elements': text_elements,
        'original_elements': ui_info['elements']
    }
    
    # 根据请求的格式保存数据
    saved_files = []
    
    # 保存为JSON格式
    if 'json' in formats:
        json_path = os.path.join(output_dir, f"{base_filename}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        saved_files.append(('JSON', json_path))
        print(f"✓ 保存JSON分析结果: {json_path}")
    
    # 保存为CSV格式（多个文件）
    if 'csv' in formats:
        # 元素基本信息CSV
        elements_csv_path = os.path.join(output_dir, f"{base_filename}_elements.csv")
        with open(elements_csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            # 写入头部
            writer.writerow(['索引', '类名', '文本', '资源ID', 'X1', 'Y1', 'X2', 'Y2', 
                           '可点击', '可滚动', '长按', '可选中', '已选中'])
            
            # 写入每个元素数据
            for i, elem in enumerate(ui_info['elements']):
                bounds = elem.get('bounds', [0, 0, 0, 0])
                writer.writerow([
                    i, 
                    elem.get('class', '').split('.')[-1],
                    elem.get('text', ''),
                    elem.get('resource-id', ''),
                    bounds[0] if len(bounds) > 0 else 0,
                    bounds[1] if len(bounds) > 1 else 0,
                    bounds[2] if len(bounds) > 2 else 0,
                    bounds[3] if len(bounds) > 3 else 0,
                    elem.get('clickable', False),
                    elem.get('scrollable', False),
                    elem.get('long-clickable', False),
                    elem.get('checkable', False),
                    elem.get('checked', False)
                ])
        
        saved_files.append(('CSV-元素', elements_csv_path))
        print(f"✓ 保存CSV元素数据: {elements_csv_path}")
        
        # 统计数据CSV
        stats_csv_path = os.path.join(output_dir, f"{base_filename}_statistics.csv")
        with open(stats_csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            # 应用信息
            writer.writerow(['应用包名', app_info['package_name']])
            writer.writerow(['活动名称', app_info['activity_name']])
            writer.writerow(['时间戳', app_info['timestamp']])
            writer.writerow(['总元素数', app_info['total_elements']])
            writer.writerow([])
            
            # 交互元素统计
            writer.writerow(['交互类型', '数量'])
            for key, value in interaction_stats.items():
                writer.writerow([key, value])
            writer.writerow([])
            
            # 深度分布
            writer.writerow(['深度', '元素数量'])
            for depth, count in sorted(depth_counts.items()):
                writer.writerow([depth, count])
            
        saved_files.append(('CSV-统计', stats_csv_path))
        print(f"✓ 保存CSV统计数据: {stats_csv_path}")
    
    # 保存为XML格式
    if 'xml' in formats:
        xml_path = os.path.join(output_dir, f"{base_filename}.xml")
        
        # 手动构建XML
        xml_content = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_content.append('<UIAnalysis>')
        
        # 应用信息
        xml_content.append('  <AppInfo>')
        xml_content.append(f'    <PackageName>{app_info["package_name"]}</PackageName>')
        xml_content.append(f'    <ActivityName>{app_info["activity_name"]}</ActivityName>')
        xml_content.append(f'    <Timestamp>{app_info["timestamp"]}</Timestamp>')
        xml_content.append(f'    <TotalElements>{app_info["total_elements"]}</TotalElements>')
        xml_content.append('  </AppInfo>')
        
        # 交互统计
        xml_content.append('  <InteractionStatistics>')
        for key, value in interaction_stats.items():
            xml_content.append(f'    <{key}>{value}</{key}>')
        xml_content.append('  </InteractionStatistics>')
        
        # 类统计
        xml_content.append('  <ClassStatistics>')
        for class_name, data in class_counts.items():
            xml_content.append(f'    <Class name="{class_name}" shortName="{data["short_name"]}" count="{data["count"]}"/>')
        xml_content.append('  </ClassStatistics>')
        
        # 深度分布
        xml_content.append('  <DepthDistribution>')
        for depth, count in sorted(depth_counts.items()):
            xml_content.append(f'    <Depth level="{depth}" count="{count}"/>')
        xml_content.append('  </DepthDistribution>')
        
        # 元素列表
        xml_content.append('  <Elements>')
        for i, elem in enumerate(ui_info['elements']):
            bounds = elem.get('bounds', [0, 0, 0, 0])
            bounds_str = f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]}" if len(bounds) == 4 else ""
            
            xml_content.append(f'    <Element index="{i}">')
            xml_content.append(f'      <Class>{elem.get("class", "")}</Class>')
            xml_content.append(f'      <Text><![CDATA[{elem.get("text", "")}]]></Text>')
            xml_content.append(f'      <ResourceId>{elem.get("resource-id", "")}</ResourceId>')
            xml_content.append(f'      <Bounds>{bounds_str}</Bounds>')
            xml_content.append(f'      <Clickable>{str(elem.get("clickable", False)).lower()}</Clickable>')
            xml_content.append(f'      <Scrollable>{str(elem.get("scrollable", False)).lower()}</Scrollable>')
            xml_content.append(f'      <LongClickable>{str(elem.get("long-clickable", False)).lower()}</LongClickable>')
            xml_content.append(f'      <Depth>{elem.get("depth", 0)}</Depth>')
            xml_content.append('    </Element>')
        
        xml_content.append('  </Elements>')
        xml_content.append('</UIAnalysis>')
        
        # 保存XML
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(xml_content))
        
        saved_files.append(('XML', xml_path))
        print(f"✓ 保存XML分析结果: {xml_path}")
    
    # 保存为HTML格式（简单报告）
    if 'html' in formats:
        html_path = os.path.join(output_dir, f"{base_filename}.html")
        
        # 构建HTML内容
        html_content = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '<meta charset="UTF-8">',
            f'<title>UI分析 - {app_info["package_name"]}</title>',
            '<style>',
            'body { font-family: Arial, sans-serif; margin: 20px; }',
            'h1, h2, h3 { color: #333; }',
            'table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }',
            'th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }',
            'th { background-color: #f2f2f2; }',
            'tr:nth-child(even) { background-color: #f9f9f9; }',
            '.stats-container { display: flex; flex-wrap: wrap; }',
            '.stats-box { flex: 1; min-width: 300px; margin: 10px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }',
            '.screenshot { max-width: 100%; border: 1px solid #ddd; margin: 10px 0; }',
            '</style>',
            '</head>',
            '<body>',
            f'<h1>UI分析报告 - {app_info["package_name"]}</h1>',
            f'<p>生成时间: {app_info["datetime"]}</p>'
        ]
        
        # 基本信息
        html_content.extend([
            '<div class="stats-container">',
            '<div class="stats-box">',
            '<h2>应用信息</h2>',
            '<table>',
            '<tr><th>属性</th><th>值</th></tr>',
            f'<tr><td>包名</td><td>{app_info["package_name"]}</td></tr>',
            f'<tr><td>活动</td><td>{app_info["activity_name"]}</td></tr>',
            f'<tr><td>总元素数</td><td>{app_info["total_elements"]}</td></tr>',
            '</table>',
            '</div>'
        ])
        
        # 交互元素统计
        html_content.extend([
            '<div class="stats-box">',
            '<h2>交互元素统计</h2>',
            '<table>',
            '<tr><th>类型</th><th>数量</th></tr>'
        ])
        
        for key, value in interaction_stats.items():
            html_content.append(f'<tr><td>{key}</td><td>{value}</td></tr>')
        
        html_content.append('</table>')
        html_content.append('</div>')
        html_content.append('</div>') # 结束 stats-container
        
        # 截图引用
        if capture_screenshot:
            screenshot_filename = f"{base_filename}.png"
            html_content.extend([
                '<h2>UI截图</h2>',
                f'<img src="{screenshot_filename}" alt="UI截图" class="screenshot">'
            ])
        
        # 元素类型统计
        html_content.extend([
            '<h2>元素类型分布</h2>',
            '<table>',
            '<tr><th>类名</th><th>简称</th><th>数量</th></tr>'
        ])
        
        # 按数量排序
        sorted_classes = sorted(class_counts.items(), key=lambda x: x[1]['count'], reverse=True)
        for class_name, data in sorted_classes:
            html_content.append(f'<tr><td>{class_name}</td><td>{data["short_name"]}</td><td>{data["count"]}</td></tr>')
        
        html_content.append('</table>')
        
        # 深度分布
        html_content.extend([
            '<h2>元素深度分布</h2>',
            '<table>',
            '<tr><th>深度</th><th>元素数量</th></tr>'
        ])
        
        for depth, count in sorted(depth_counts.items()):
            html_content.append(f'<tr><td>{depth}</td><td>{count}</td></tr>')
        
        html_content.append('</table>')
        
        # 文本元素表格
        html_content.extend([
            '<h2>文本元素 (前20个)</h2>',
            '<table>',
            '<tr><th>索引</th><th>文本</th><th>类型</th><th>可点击</th></tr>'
        ])
        
        for i, elem in enumerate(text_elements[:20]):  # 限制为前20个
            html_content.append(f'<tr><td>{elem["element_index"]}</td><td>{elem["text"]}</td>'
                               f'<td>{elem["class"]}</td><td>{str(elem["clickable"]).lower()}</td></tr>')
        
        html_content.append('</table>')
        
        # 结束HTML
        html_content.extend([
            '<p><small>由PPADB工具生成</small></p>',
            '</body>',
            '</html>'
        ])
        
        # 保存HTML
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_content))
        
        saved_files.append(('HTML', html_path))
        print(f"✓ 保存HTML报告: {html_path}")
    
    # 打开HTML报告（如果存在）
    if 'html' in formats:
        try:
            if os.name == 'nt':  # Windows
                os.startfile(html_path)
            elif os.name == 'posix':  # Linux/Mac
                if sys.platform == 'darwin':  # Mac
                    os.system(f'open "{html_path}"')
                else:  # Linux
                    os.system(f'xdg-open "{html_path}"')
        except:
            print("请手动打开HTML报告查看分析结果")
    
    # 返回保存的文件列表
    return {
        'success': True,
        'message': f'成功保存UI分析结果 ({len(saved_files)} 个文件)',
        'saved_files': saved_files,
        'app_info': app_info,
        'element_count': len(ui_info['elements']),
        'output_dir': output_dir
    }


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='UI分析结果保存工具')
    parser.add_argument('-o', '--output', type=str, default=None,
                      help='输出目录 (默认为脚本所在目录)')
    parser.add_argument('-f', '--formats', type=str, default='json,html',
                      help='保存格式，用逗号分隔 (可选: json,csv,xml,html)')
    parser.add_argument('-n', '--no-screenshot', action='store_true',
                      help='不捕获屏幕截图，只保存分析数据')
    parser.add_argument('-m', '--max-elements', type=int, default=200,
                      help='截图中标记的最大元素数量 (默认200)')
    args = parser.parse_args()
    
    # 解析保存格式
    formats = [fmt.strip().lower() for fmt in args.formats.split(',')]
    
    # 执行保存
    result = save_ui_analysis(
        output_dir=args.output,
        formats=formats,
        capture_screenshot=not args.no_screenshot,
        max_elements=args.max_elements
    )
    
    if result['success']:
        print("\n✓ UI分析完成!")
        print(f"✓ 已将分析结果保存到: {result['output_dir']}")
    else:
        print(f"\n❌ UI分析失败: {result['message']}")


if __name__ == "__main__":
    main() 