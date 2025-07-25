import time
import pathlib
import sys

current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

current_dir = pathlib.Path(__file__).parent
root_dir = current_dir.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

def find_elements_by_role(browser_tool, page_index=None, role_value=None, exact_match=None, 
                         tag_type=None, include_iframes=None):
    """通过role属性查找元素
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要查找元素的页面序号
        role_value: 要查找的role值 (例如: button, group, listitem)
        exact_match: 是否精确匹配role值，默认True
        tag_type: 限制元素类型，如'div', 'a', 'button'等
        include_iframes: 是否在iframe中查找元素，默认True
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取要查询的页面序号
    if page_index is None:
        page_index = 0  # 默认使用第一个页面
        
    # 输入要查找的role值
    if role_value is None:
        print("错误: 必须提供role_value参数")
        return
    
    # 询问是否需要精确匹配
    if exact_match is None:
        exact_match = True  # 默认精确匹配
    
    # 询问是否要限制元素类型
    if tag_type is None:
        tag_type = None  # 默认不限制元素类型
    
    # 是否包含iframe中的元素
    if include_iframes is None:
        include_iframes = True  # 默认包含iframe
    
    # 创建JavaScript查找代码
    js_code = """
    (params) => {
        const roleValue = params.roleValue;
        const tagType = params.tagType;
        const exactMatch = params.exactMatch;
        
        // 构建查询选择器
        let selector = '';
        if (tagType) {
            // 如果指定了标签类型
            selector = tagType;
        } else {
            // 默认查找所有元素
            selector = '*';
        }
        
        // 获取所有匹配标签类型的元素
        const allElements = Array.from(document.querySelectorAll(selector));
        
        // 过滤符合role条件的元素
        const matchedElements = allElements.filter(element => {
            const roleAttr = element.getAttribute('role');
            if (!roleAttr) return false;
            
            if (exactMatch) {
                // 精确匹配 - role必须完全一致
                return roleAttr === roleValue;
            } else {
                // 包含匹配 - 元素的role中包含查询的role值
                return roleAttr.includes(roleValue);
            }
        });
        
        // 构建结果
        const results = matchedElements.map(element => {
            // 获取元素位置
            const rect = element.getBoundingClientRect();
            
            // 获取元素文本内容
            const text = element.innerText || element.textContent || '';
            
            // 获取CSS选择器
            let path = [];
            let currentElement = element;
            while (currentElement && currentElement.nodeType === Node.ELEMENT_NODE) {
                let selector = currentElement.nodeName.toLowerCase();
                if (currentElement.id) {
                    selector += '#' + currentElement.id;
                    path.unshift(selector);
                    break;
                } else if (currentElement.className) {
                    const classes = currentElement.className.split(/\\s+/);
                    if (classes.length > 0) {
                        selector += '.' + classes.join('.');
                    }
                }
                
                // 添加role属性到选择器
                const role = currentElement.getAttribute('role');
                if (role) {
                    selector += `[role="${role}"]`;
                }
                
                let sibling = currentElement;
                let index = 1;
                while (sibling = sibling.previousElementSibling) {
                    if (sibling.nodeName.toLowerCase() === selector.split('.')[0].split('[')[0]) {
                        index++;
                    }
                }
                
                if (index > 1) {
                    selector += ':nth-of-type(' + index + ')';
                }
                
                path.unshift(selector);
                
                // 向上查找父元素
                currentElement = currentElement.parentNode;
                
                // 限制选择器长度
                if (path.length >= 3) {
                    break;
                }
            }
            
            const cssSelector = path.join(' > ');
            
            // 构建元素信息
            return {
                tagName: element.tagName.toLowerCase(),
                role: element.getAttribute('role'),
                text: text.substring(0, 100),
                cssSelector: cssSelector,
                rect: {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                },
                isVisible: element.offsetParent !== null && 
                          element.offsetWidth > 0 && 
                          element.offsetHeight > 0,
                attributes: Array.from(element.attributes).reduce((acc, attr) => {
                    acc[attr.name] = attr.value;
                    return acc;
                }, {})
            };
        });
        
        // 只返回可见元素
        return results.filter(el => el.isVisible);
    }
    """
    
    print(f"\n正在页面 {page_index} 中查找role为 '{role_value}' 的元素...")
    print(f"精确匹配: {'是' if exact_match else '否'}")
    print(f"元素类型: {tag_type if tag_type else '所有类型'}")
    print(f"包含iframe: {'是' if include_iframes else '否'}")
    
    try:
        # 在主页面中查找元素
        elements = browser_tool._async_loop.run_until_complete(
            browser_tool.context.pages[page_index].evaluate(js_code, {
                'roleValue': role_value,
                'tagType': tag_type,
                'exactMatch': exact_match
            })
        )
        
        main_elements = elements
        iframe_elements = []
        
        # 如果需要，在iframe中也查找元素
        if include_iframes:
            # 获取所有iframe
            iframe_handles = browser_tool._async_loop.run_until_complete(
                browser_tool.context.pages[page_index].query_selector_all('iframe')
            )
            
            if iframe_handles:
                print(f"发现 {len(iframe_handles)} 个iframe，正在检查...")
                
                # 遍历iframe查找元素
                for i, iframe_handle in enumerate(iframe_handles):
                    try:
                        # 获取iframe信息
                        iframe_id = browser_tool._async_loop.run_until_complete(
                            iframe_handle.get_attribute('id')
                        ) or f"iframe_{i}"
                        
                        iframe_name = browser_tool._async_loop.run_until_complete(
                            iframe_handle.get_attribute('name')
                        ) or iframe_id
                        
                        iframe_src = browser_tool._async_loop.run_until_complete(
                            iframe_handle.get_attribute('src')
                        ) or ""
                        
                        # 获取iframe内容框架
                        content_frame = browser_tool._async_loop.run_until_complete(
                            iframe_handle.content_frame()
                        )
                        
                        if content_frame:
                            # 在iframe中查找元素
                            iframe_result = browser_tool._async_loop.run_until_complete(
                                content_frame.evaluate(js_code, {
                                    'roleValue': role_value,
                                    'tagType': tag_type,
                                    'exactMatch': exact_match
                                })
                            )
                            
                            if iframe_result and len(iframe_result) > 0:
                                print(f"在iframe '{iframe_name}' 中找到 {len(iframe_result)} 个匹配元素")
                                
                                # 获取iframe位置
                                iframe_rect = browser_tool._async_loop.run_until_complete(
                                    iframe_handle.bounding_box()
                                )
                                
                                # 将iframe信息添加到每个元素
                                for el in iframe_result:
                                    el['from_iframe'] = True
                                    el['iframe_id'] = iframe_id
                                    el['iframe_name'] = iframe_name
                                    el['iframe_src'] = iframe_src
                                    el['iframe_index'] = i
                                    
                                    if iframe_rect:
                                        el['iframe_rect'] = iframe_rect
                                        
                                        # 调整元素位置，加上iframe的偏移量
                                        if 'rect' in el:
                                            el['rect']['x'] += iframe_rect['x']
                                            el['rect']['y'] += iframe_rect['y']
                                
                                iframe_elements.extend(iframe_result)
                        
                    except Exception as e:
                        print(f"处理iframe '{iframe_id}' 时出错: {str(e)}")
                        continue
                    finally:
                        # 释放iframe句柄
                        browser_tool._async_loop.run_until_complete(iframe_handle.dispose())
        
        # 合并所有结果
        all_elements = main_elements + iframe_elements
        
        # 显示结果
        print(f"\n找到 {len(all_elements)} 个匹配元素:")
        print(f"- 主页面: {len(main_elements)} 个元素")
        print(f"- iframe内: {len(iframe_elements)} 个元素")
        
        if all_elements:
            for i, element in enumerate(all_elements):
                # 基本信息
                tag_name = element.get('tagName', '')
                role_attr = element.get('role', '')
                
                # 文本内容
                text = element.get('text', '').strip()
                if len(text) > 40:
                    text = text[:37] + "..."
                
                # 是否来自iframe
                from_iframe = element.get('from_iframe', False)
                iframe_info = ""
                if from_iframe:
                    iframe_name = element.get('iframe_name', '')
                    iframe_info = f" [来自iframe: {iframe_name}]"
                
                # 显示元素信息
                print(f"\n[{i+1}] <{tag_name}> role=\"{role_attr}\" '{text}'{iframe_info}")
                print(f"    选择器: {element.get('cssSelector', '')}")
                
                # 显示位置信息
                rect = element.get('rect', {})
                print(f"    位置: x={rect.get('x', 0):.0f}, y={rect.get('y', 0):.0f}, "
                      f"宽={rect.get('width', 0):.0f}, 高={rect.get('height', 0):.0f}")
                
                # 显示其他属性
                attributes = element.get('attributes', {})
                if attributes:
                    print("    属性:")
                    for attr_name, attr_value in attributes.items():
                        if attr_name != 'role':  # role已经单独显示
                            print(f"      {attr_name}=\"{attr_value}\"")
            
            # 提示信息，不再进行交互式操作
            print("\n提示：使用auto_click=True和相关参数来自动操作元素")
            return {
                "success": True,
                "message": "元素查找完成，使用auto_click参数来进行自动操作",
                "elements": all_elements,
                "total_elements": len(all_elements)
            }
            
        # 这里添加一个永远不会执行的条件，确保下面的代码不被执行
        if False:
                try:
                    element_index = int(input("请输入要操作的元素序号: ")) - 1
                    if element_index < 0 or element_index >= len(all_elements):
                        print(f"无效的序号，有效范围: 1-{len(all_elements)}")
                        return
                    
                    selected_element = all_elements[element_index]
                    selector = selected_element.get('cssSelector', '')
                    
                    # 是否来自iframe
                    from_iframe = selected_element.get('from_iframe', False)
                    
                    # 显示操作选项
                    print("\n请选择操作类型:")
                    print("1. 点击 (默认)")
                    print("2. 双击")
                    print("3. 悬停")
                    print("4. 高亮显示")
                    print("5. 截图元素")
                    print("6. 保存元素")
                    print("7. 输入文本")
                    
                    operation = input("请选择操作 (1-7): ") or "1"
                    
                    # 进行操作
                    if from_iframe:
                        # iframe内的元素需要特殊处理
                        iframe_index = selected_element.get('iframe_index', 0)
                        
                        try:
                            # 获取iframe句柄
                            iframe_handles = browser_tool._async_loop.run_until_complete(
                                browser_tool.context.pages[page_index].query_selector_all('iframe')
                            )
                            
                            if iframe_index < len(iframe_handles):
                                iframe_handle = iframe_handles[iframe_index]
                                content_frame = browser_tool._async_loop.run_until_complete(
                                    iframe_handle.content_frame()
                                )
                                
                                if content_frame:
                                    # 在iframe中查找元素
                                    element_handle = browser_tool._async_loop.run_until_complete(
                                        content_frame.query_selector(selector)
                                    )
                                    
                                    if not element_handle:
                                        print(f"在iframe中未找到元素: {selector}")
                                        return
                                    
                                    # 根据操作类型执行不同操作
                                    if operation == "1":
                                        # 点击
                                        print(f"\n正在点击iframe内的元素...")
                                        browser_tool._async_loop.run_until_complete(
                                            element_handle.click()
                                        )
                                        print("点击成功!")
                                    elif operation == "2":
                                        # 双击
                                        print(f"\n正在双击iframe内的元素...")
                                        browser_tool._async_loop.run_until_complete(
                                            element_handle.dblclick()
                                        )
                                        print("双击成功!")
                                    elif operation == "3":
                                        # 悬停
                                        print(f"\n正在悬停在iframe内的元素上...")
                                        browser_tool._async_loop.run_until_complete(
                                            element_handle.hover()
                                        )
                                        print("悬停成功!")
                                    elif operation == "4":
                                        # 高亮显示
                                        print(f"\n正在高亮显示iframe内的元素...")
                                        browser_tool._async_loop.run_until_complete(
                                            content_frame.evaluate(f"""
                                                (selector) => {{
                                                    const el = document.querySelector(selector);
                                                    if (el) {{
                                                        // 保存原始样式
                                                        el._originalOutline = el.style.outline;
                                                        el._originalBoxShadow = el.style.boxShadow;
                                                        
                                                        // 添加高亮效果
                                                        el.style.outline = '2px solid red';
                                                        el.style.boxShadow = '0 0 10px rgba(255,0,0,0.5)';
                                                        
                                                        // 5秒后恢复原样
                                                        setTimeout(() => {{
                                                            el.style.outline = el._originalOutline;
                                                            el.style.boxShadow = el._originalBoxShadow;
                                                        }}, 5000);
                                                    }}
                                                }}
                                            """, selector)
                                        )
                                        print("高亮显示成功! (5秒后自动消失)")
                                    elif operation == "5":
                                        # 截图
                                        print(f"\n正在截图iframe内的元素...")
                                        
                                        # 生成文件名
                                        default_filename = f"element_iframe_{iframe_index}_{int(time.time())}.png"
                                        file_path = input(f"\n请输入保存路径和文件名 (默认: {default_filename}): ") or default_filename
                                        
                                        # 确保文件名有扩展名
                                        if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                                            file_path += '.png'
                                        
                                        # 获取元素截图
                                        result = browser_tool._async_loop.run_until_complete(
                                            element_handle.screenshot(path=file_path)
                                        )
                                        
                                        print(f"元素截图已保存至: {file_path}")
                                    elif operation == "6":
                                        # 保存元素
                                        print(f"\n正在保存iframe内的元素...")
                                        
                                        # 将element转换为可保存的格式
                                        element_to_save = selected_element
                                        
                                        # 询问保存名称
                                        element_name = input("请输入保存的元素名称 (留空将自动生成): ")
                                        
                                        # 保存元素
                                        save_result = browser_tool.save_elements([element_to_save], prefix=element_name)
                                        
                                        if save_result['success']:
                                            print(f"元素已保存: {save_result['element_names']}")
                                        else:
                                            print(f"保存元素失败: {save_result['message']}")
                                    elif operation == "7":
                                        # 输入文本
                                        print(f"\n正在准备向iframe内的元素输入文本...")
                                        text_to_input = input("请输入要输入的文本: ")
                                        if text_to_input:
                                            # 先点击元素获取焦点
                                            browser_tool._async_loop.run_until_complete(
                                                element_handle.click()
                                            )
                                            # 清空现有内容
                                            browser_tool._async_loop.run_until_complete(
                                                content_frame.evaluate(f"""
                                                    (selector) => {{
                                                        const el = document.querySelector(selector);
                                                        if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {{
                                                            el.value = '';
                                                        }} else if (el && el.isContentEditable) {{
                                                            el.innerHTML = '';
                                                        }}
                                                    }}
                                                """, selector)
                                            )
                                            # 输入新文本
                                            browser_tool._async_loop.run_until_complete(
                                                element_handle.type(text_to_input)
                                            )
                                            print(f"文本输入成功: \"{text_to_input}\"")
                                        else:
                                            print("未输入任何文本，操作取消")
                                else:
                                    print("无法获取iframe内容框架")
                            else:
                                print(f"无法获取iframe (索引: {iframe_index})")
                        except Exception as e:
                            print(f"操作iframe内元素时出错: {str(e)}")
                    else:
                        # 主页面中的元素
                        if operation == "1":
                            # 点击
                            wait_nav = input("\n是否等待页面导航? (y/n, 默认是): ")
                            wait_for_navigation = wait_nav.lower() != 'n'
                            
                            click_result = browser_tool.click_element(
                                page_index=page_index,
                                element_selector=selector,
                                click_type='click',
                                wait_for_navigation=wait_for_navigation
                            )
                            
                            if click_result['success']:
                                print(f"点击成功!")
                                print(f"页面标题: {click_result['title']}")
                                print(f"页面URL: {click_result['url']}")
                            else:
                                print(f"点击失败: {click_result['message']}")
                        elif operation == "2":
                            # 双击
                            click_result = browser_tool.click_element(
                                page_index=page_index,
                                element_selector=selector,
                                click_type='dblclick',
                                wait_for_navigation=False
                            )
                            
                            if click_result['success']:
                                print(f"双击成功!")
                            else:
                                print(f"双击失败: {click_result['message']}")
                        elif operation == "3":
                            # 悬停
                            hover_result = browser_tool.click_element(
                                page_index=page_index,
                                element_selector=selector,
                                click_type='hover',
                                wait_for_navigation=False
                            )
                            
                            if hover_result['success']:
                                print(f"悬停成功!")
                            else:
                                print(f"悬停失败: {hover_result['message']}")
                        elif operation == "4":
                            # 高亮显示
                            print(f"\n正在高亮显示元素...")
                            
                            highlight_result = browser_tool._async_loop.run_until_complete(
                                browser_tool.context.pages[page_index].evaluate(f"""
                                    (selector) => {{
                                        const el = document.querySelector(selector);
                                        if (el) {{
                                            // 保存原始样式
                                            el._originalOutline = el.style.outline;
                                            el._originalBoxShadow = el.style.boxShadow;
                                            
                                            // 添加高亮效果
                                            el.style.outline = '2px solid red';
                                            el.style.boxShadow = '0 0 10px rgba(255,0,0,0.5)';
                                            
                                            // 5秒后恢复原样
                                            setTimeout(() => {{
                                                el.style.outline = el._originalOutline;
                                                el.style.boxShadow = el._originalBoxShadow;
                                            }}, 5000);
                                            
                                            return true;
                                        }}
                                        return false;
                                    }}
                                """, selector)
                            )
                            
                            if highlight_result:
                                print("高亮显示成功! (5秒后自动消失)")
                            else:
                                print(f"高亮显示失败: 找不到元素 {selector}")
                        elif operation == "5":
                            # 截图
                            print(f"\n正在截图元素...")
                            
                            # 生成文件名
                            default_filename = f"element_{int(time.time())}.png"
                            file_path = input(f"\n请输入保存路径和文件名 (默认: {default_filename}): ") or default_filename
                            
                            # 确保文件名有扩展名
                            if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                                file_path += '.png'
                            
                            # 获取元素句柄
                            element_handle = browser_tool._async_loop.run_until_complete(
                                browser_tool.context.pages[page_index].query_selector(selector)
                            )
                            
                            if element_handle:
                                # 截图
                                result = browser_tool._async_loop.run_until_complete(
                                    element_handle.screenshot(path=file_path)
                                )
                                print(f"元素截图已保存至: {file_path}")
                            else:
                                print(f"截图失败: 找不到元素 {selector}")
                        elif operation == "6":
                            # 保存元素
                            print(f"\n正在保存元素...")
                            
                            # 将element转换为可保存的格式
                            element_to_save = selected_element
                            
                            # 询问保存名称
                            element_name = input("请输入保存的元素名称 (留空将自动生成): ")
                            
                            # 保存元素
                            save_result = browser_tool.save_elements([element_to_save], prefix=element_name)
                            
                            if save_result['success']:
                                print(f"元素已保存: {save_result['element_names']}")
                            else:
                                print(f"保存元素失败: {save_result['message']}")
                        elif operation == "7":
                            # 输入文本
                            print(f"\n正在准备向元素输入文本...")
                            text_to_input = input("请输入要输入的文本: ")
                            if text_to_input:
                                # 获取元素
                                element = browser_tool._async_loop.run_until_complete(
                                    browser_tool.context.pages[page_index].query_selector(selector)
                                )
                                
                                if element:
                                    # 先点击元素获取焦点
                                    browser_tool._async_loop.run_until_complete(
                                        element.click()
                                    )
                                    # 清空现有内容
                                    browser_tool._async_loop.run_until_complete(
                                        browser_tool.context.pages[page_index].evaluate(f"""
                                            (selector) => {{
                                                const el = document.querySelector(selector);
                                                if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {{
                                                    el.value = '';
                                                }} else if (el && el.isContentEditable) {{
                                                    el.innerHTML = '';
                                                }}
                                            }}
                                        """, selector)
                                    )
                                    # 输入新文本
                                    browser_tool._async_loop.run_until_complete(
                                        element.type(text_to_input)
                                    )
                                    print(f"文本输入成功: \"{text_to_input}\"")
                                else:
                                    print(f"未找到元素: {selector}")
                            else:
                                print("未输入任何文本，操作取消")
                        else:
                            print("无效的操作类型")
                except ValueError as e:
                    print(f"输入错误: {str(e)}")
                except Exception as e:
                    print(f"执行操作时出错: {str(e)}")
        else:
            print(f"未找到匹配的元素")
    
    except Exception as e:
        import traceback
        print(f"查找元素时出错: {str(e)}")
        print(traceback.format_exc()) 