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

def find_elements_by_class(browser_tool, page_index=None, class_name=None, 
                          exact_match=None, tag_type=None, include_iframes=None):
    """通过类名精确查找元素
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要查找元素的页面序号
        class_name: 要查找的类名
        exact_match: 是否精确匹配类名，默认True
        tag_type: 限制元素类型，如'div', 'a', 'button'等
        include_iframes: 是否在iframe中查找元素，默认True
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取要查询的页面序号
    if page_index is None:
        page_index = 0  # 默认使用第一个页面
        
    # 输入要查找的类名
    if class_name is None:
        print("错误: 必须提供class_name参数")
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
        const className = params.className;
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
        
        // 过滤符合类名条件的元素
        const matchedElements = allElements.filter(element => {
            if (!element.className) return false;
            
            // 处理SVG元素等特殊情况，确保className是字符串
            let classValue = '';
            if (typeof element.className === 'string') {
                classValue = element.className;
            } else if (element.className.baseVal !== undefined) {
                // SVG元素的className是一个SVGAnimatedString对象
                classValue = element.className.baseVal;
            } else {
                // 其他情况尝试转换为字符串
                try {
                    classValue = String(element.className);
                } catch (e) {
                    return false;
                }
            }
            
            if (!classValue) return false;
            
            const classNames = classValue.split(' ');
            
            if (exactMatch) {
                // 精确匹配 - 类名必须完全一致
                return classValue === className;
            } else {
                // 包含匹配 - 元素的类名中包含查询的类名
                return classNames.some(cls => cls === className) || 
                       classValue.includes(className);
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
                
                let sibling = currentElement;
                let index = 1;
                while (sibling = sibling.previousElementSibling) {
                    if (sibling.nodeName.toLowerCase() === selector.split('.')[0]) {
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
                className: element.className,
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
                          element.offsetHeight > 0
            };
        });
        
        // 只返回可见元素
        return results.filter(el => el.isVisible);
    }
    """
    
    print(f"\n正在页面 {page_index} 中查找类名为 '{class_name}' 的元素...")
    print(f"精确匹配: {'是' if exact_match else '否'}")
    print(f"元素类型: {tag_type if tag_type else '所有类型'}")
    print(f"包含iframe: {'是' if include_iframes else '否'}")
    
    try:
        # 在主页面中查找元素
        elements = browser_tool._async_loop.run_until_complete(
            browser_tool.context.pages[page_index].evaluate(js_code, {
                'className': class_name,
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
                                    'className': class_name,
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
                class_value = element.get('className', '')
                
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
                print(f"\n[{i+1}] <{tag_name}> '{text}'{iframe_info}")
                print(f"    类名: {class_value}")
                print(f"    选择器: {element.get('cssSelector', '')}")
                
                # 显示位置信息
                rect = element.get('rect', {})
                print(f"    位置: x={rect.get('x', 0):.0f}, y={rect.get('y', 0):.0f}, "
                      f"宽={rect.get('width', 0):.0f}, 高={rect.get('height', 0):.0f}")
            
            # 提示信息，不再进行交互式操作
            print("\n提示：使用auto_click=True和相关参数来自动操作元素")
            return {
                "success": True,
                "message": "元素查找完成，使用auto_click参数来进行自动操作",
                "elements": all_elements,
                "total_elements": len(all_elements)
            }
        else:
            print("未找到匹配的元素")
            return {
                "success": False,
                "message": "未找到符合条件的元素",
                "elements": [],
                "total_elements": 0,
                "error_type": "element_not_found"  # 🔧 明确标识：页面正常但搜不到元素
            }
    
    except Exception as e:
        error_msg = str(e).lower()
        print(f"查找元素时发生错误: {str(e)}")
        
        # 🔧 根据错误消息判断错误类型
        if any(keyword in error_msg for keyword in ['target crashed', 'page crashed', 'target closed', 'browser crashed']):
            # 浏览器崩溃错误
            return {
                "success": False,
                "message": f"查找元素时发生错误: {str(e)}",
                "elements": [],
                "total_elements": 0,
                "error_type": "browser_crash"  # 🔧 明确标识：浏览器崩溃
            }
        elif any(keyword in error_msg for keyword in ['websocket', 'connection', 'disconnected', 'network']):
            # 网络连接错误
            return {
                "success": False,
                "message": f"查找元素时发生错误: {str(e)}",
                "elements": [],
                "total_elements": 0,
                "error_type": "connection_error"  # 🔧 明确标识：连接错误
            }
        else:
            # 其他未知错误
            return {
                "success": False,
                "message": f"查找元素时发生错误: {str(e)}",
                "elements": [],
                "total_elements": 0,
                "error_type": "unknown_error"  # 🔧 明确标识：未知错误
            }