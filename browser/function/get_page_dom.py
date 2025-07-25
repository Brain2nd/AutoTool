import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))



def get_page_dom(browser_tool, page_index=None, selector=None, save_to_file=None):
    """获取指定页面的DOM结构
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要获取DOM的页面序号
        selector: CSS选择器，默认为'html'(整个页面)
        save_to_file: 是否保存DOM到文件，默认为None(询问用户)
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取要查询的页面序号
    if page_index is None:
        print("错误: 必须指定要获取DOM的页面序号")
        return
    
    # 设置默认选择器
    if selector is None:
        selector = 'html'  # 默认选择整个页面
    
    print(f"\n正在获取页面 {page_index} 的DOM结构 {f'(选择器: {selector})' if selector != 'html' else '(整个页面)'}...")
    print("注意: 复杂页面可能需要较长时间，正在递归获取iframe内容...")
    
    result = browser_tool.get_page_dom(page_index, selector)
    
    if not result['success']:
        print(f"获取DOM失败: {result['message']}")
        return
    
    # 获取DOM大小信息
    dom_size = result.get('size', 0)
    
    print(f"获取DOM成功! {result['message']}")
    print(f"页面标题: {result['title']}")
    print(f"页面URL: {result['url']}")
    print(f"DOM大小: {dom_size} 字符 ({dom_size/1024:.2f} KB)")
    
    # 显示iframe信息（如果有）
    if result.get('has_iframes', False):
        print(f"\n发现 {result.get('iframe_count', 0)} 个iframe:")
        if 'iframes' in result:
            for name, iframe_data in result['iframes'].items():
                iframe_size = len(iframe_data['html']) if isinstance(iframe_data['html'], str) else 0
                print(f"  - {name}: {iframe_size} 字符 ({iframe_size/1024:.2f} KB)")
                print(f"    源地址: {iframe_data['src']}")
    
    # 显示DOM的一部分，避免输出过多
    print("\nDOM预览:")
    
    # 根据结果结构决定如何显示DOM内容
    if isinstance(result['dom'], dict) and 'main_html' in result['dom']:
        # 增强的DOM结构（包含iframe内容）
        main_html = result['dom']['main_html']
        preview_length = min(1000, len(main_html))
        print(f"主页面DOM内容 (共 {len(main_html)} 字符):")
        print(f"{main_html[:preview_length]}...")
    else:
        # 普通字符串DOM
        dom = result['dom']
        preview_length = min(1000, len(dom))
        print(f"DOM内容 (共 {len(dom)} 字符):")
        print(f"{dom[:preview_length]}...")
    
    # 自动保存模式或设置默认不保存
    if save_to_file is None:
        save_to_file = False  # 默认不保存到文件
    
    if save_to_file:
        _save_dom_to_file(result, page_index, dom_size)
                
    # 提供返回DOM的选项（用于调试或进一步处理）
    return result


def _save_dom_to_file(result, page_index, dom_size):
    """保存DOM到文件的辅助函数"""
    # 大型DOM的保存选项
    if dom_size > 1024 * 1024:  # 如果DOM大于1MB
        save_option = '2'  # 默认按模块分割保存
        print("DOM较大，将按模块分割保存")
        
        if save_option == '2':
            try:
                # 创建目录
                import os
                dir_name = f"page_{page_index}_dom_parts"
                os.makedirs(dir_name, exist_ok=True)
                
                # 根据结果类型决定保存方式
                if result.get('has_iframes', False) and 'iframes' in result:
                    # 保存主页面
                    main_html = result['dom'] if isinstance(result['dom'], str) else result['dom'].get('main_html', '')
                    with open(f"{dir_name}/00_main_page.html", 'w', encoding='utf-8') as f:
                        f.write(main_html)
                    
                    # 保存每个iframe内容
                    for name, iframe_data in result['iframes'].items():
                        iframe_html = iframe_data['html']
                        safe_name = ''.join(c if c.isalnum() else '_' for c in name)
                        with open(f"{dir_name}/iframe_{safe_name}.html", 'w', encoding='utf-8') as f:
                            f.write(iframe_html if isinstance(iframe_html, str) else str(iframe_html))
                    
                    # 创建索引文件
                    with open(f"{dir_name}/index.html", 'w', encoding='utf-8') as f:
                        f.write("<html><head><title>DOM with iframes</title></head><body>")
                        f.write(f"<h1>页面 {page_index} DOM 分析</h1>")
                        f.write(f"<p>标题: {result['title']}</p>")
                        f.write(f"<p>URL: {result['url']}</p>")
                        
                        f.write("<h2>主页面</h2>")
                        f.write(f'<p><a href="00_main_page.html" target="_blank">查看主页面</a></p>')
                        
                        f.write(f"<h2>iframes ({len(result['iframes'])}个)</h2>")
                        f.write("<ul>")
                        for name, iframe_data in result['iframes'].items():
                            safe_name = ''.join(c if c.isalnum() else '_' for c in name)
                            iframe_size = len(iframe_data['html']) if isinstance(iframe_data['html'], str) else 0
                            f.write(f'<li><a href="iframe_{safe_name}.html" target="_blank">{name}</a> - {iframe_size/1024:.2f} KB')
                            f.write(f'<br>Source: {iframe_data["src"]}</li>')
                        f.write("</ul></body></html>")
                    
                    print(f"DOM和iframe内容已保存到目录: {dir_name}")
                    print(f"- 索引文件: {dir_name}/index.html")
                else:
                    # 标准DOM分析和保存
                    import re
                    dom = result['dom']
                    parts = []
                    
                    # 提取head部分
                    head_match = re.search(r'(<head.*?>.*?</head>)', dom, re.DOTALL)
                    if head_match:
                        with open(f"{dir_name}/01_head.html", 'w', encoding='utf-8') as f:
                            f.write(head_match.group(1))
                        parts.append("01_head.html")
                    
                    # 提取body部分
                    body_match = re.search(r'(<body.*?>)(.*?)(</body>)', dom, re.DOTALL)
                    if body_match:
                        body_opening = body_match.group(1)
                        body_content = body_match.group(2)
                        body_closing = body_match.group(3)
                        
                        with open(f"{dir_name}/02_body_opening.html", 'w', encoding='utf-8') as f:
                            f.write(body_opening)
                        parts.append("02_body_opening.html")
                        
                        # 分析主要部分（根据顶级div或section分割）
                        main_parts = re.findall(r'(<(?:div|section|main|article|header|footer|nav)(?:\s+[^>]*?)?>.*?</(?:div|section|main|article|header|footer|nav)>)', body_content, re.DOTALL)
                        
                        if main_parts:
                            for i, part in enumerate(main_parts, start=1):
                                # 跳过过小的部分
                                if len(part) < 100:
                                    continue
                                
                                part_filename = f"03_body_part_{i:02d}.html"
                                with open(f"{dir_name}/{part_filename}", 'w', encoding='utf-8') as f:
                                    f.write(part)
                                parts.append(part_filename)
                        else:
                            # 如果没有找到主要部分，则整体保存body内容
                            with open(f"{dir_name}/03_body_content.html", 'w', encoding='utf-8') as f:
                                f.write(body_content)
                            parts.append("03_body_content.html")
                        
                        with open(f"{dir_name}/04_body_closing.html", 'w', encoding='utf-8') as f:
                            f.write(body_closing)
                        parts.append("04_body_closing.html")
                    
                    # 创建一个索引文件
                    with open(f"{dir_name}/index.html", 'w', encoding='utf-8') as f:
                        f.write("<html><head><title>DOM Parts Index</title></head><body>")
                        f.write(f"<h1>页面 {page_index} DOM 分段索引</h1>")
                        f.write(f"<p>标题: {result['title']}</p>")
                        f.write(f"<p>URL: {result['url']}</p>")
                        f.write("<ul>")
                        for part in parts:
                            f.write(f'<li><a href="{part}">{part}</a></li>')
                        f.write("</ul></body></html>")
                    
                    print(f"DOM已分段保存到目录: {dir_name}")
                    print(f"- 分为 {len(parts)} 个部分")
                    print(f"- 索引文件: {dir_name}/index.html")
            except Exception as e:
                print(f"分段保存DOM时出错: {str(e)}")
        else:
            # 保存完整DOM
            _save_complete_dom(result, page_index)
    else:
        # 普通大小DOM直接保存
        _save_complete_dom(result, page_index)


def _save_complete_dom(result, page_index):
    """保存完整DOM到文件的辅助函数"""
    if result.get('has_iframes', False):
        # 如果包含iframe，保存为JSON格式
        filename = f"page_{page_index}_dom_with_iframes.json"
        try:
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                # 创建可序列化的结构
                save_data = {
                    'title': result['title'],
                    'url': result['url'],
                    'has_iframes': True,
                    'iframe_count': result['iframe_count'],
                    'main_html': result['dom'] if isinstance(result['dom'], str) else result['dom'].get('main_html', ''),
                    'iframes': {}
                }
                
                # 添加iframe数据
                if 'iframes' in result:
                    for name, iframe_data in result['iframes'].items():
                        save_data['iframes'][name] = {
                            'id': iframe_data['id'],
                            'src': iframe_data['src'],
                            'html': iframe_data['html'] if isinstance(iframe_data['html'], str) else str(iframe_data['html'])
                        }
                
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            print(f"DOM和iframe数据已保存到文件: {filename}")
        except Exception as e:
            print(f"保存文件时出错: {str(e)}")
    else:
        # 保存为普通HTML
        filename = f"page_{page_index}_dom_full.html"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result['dom'])
            print(f"完整DOM已保存到文件: {filename}")
        except Exception as e:
            print(f"保存文件时出错: {str(e)}")
