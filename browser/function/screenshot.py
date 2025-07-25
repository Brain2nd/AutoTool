import pathlib
import sys
import time
import os
import shutil
import json
from PIL import Image  # 添加PIL支持


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# 导入分析模块
from .analysis import analysis_resume

# 创建缓存目录
cache_dir = os.path.join(current_dir, "cache")
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

def screenshot(browser_tool, page_index=None, auto_analysis=False, screenshot_type=None, 
               file_path=None, element_selector=None, class_name=None, search_text=None):
    """获取页面截图
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要截图的页面序号
        auto_analysis: 是否自动分析截图
        screenshot_type: 截图类型 ('1'=可视区域, '2'=完整页面, '3'=元素截图, '4'=滚动截图, '5'=PDF查看器)
        file_path: 保存路径和文件名
        element_selector: 元素选择器(用于元素截图)
        class_name: 类名(用于通过类名截图)
        search_text: 搜索文本(用于通过文本截图)
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取要截图的页面序号
    if page_index is None:
        print("错误: 必须指定要截图的页面序号")
        return
    
    # 设置截图类型
    if screenshot_type is None:
        screenshot_type = "1"  # 默认为可视区域截图
    
    # 文件路径和名称处理
    if file_path is None:
        timestamp = int(time.time())
        default_filename = f"screenshot_page{page_index}_{timestamp}.png"
        file_path = os.path.join(cache_dir, default_filename)
    
    # 确保文件名有扩展名
    if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        file_path += '.png'
    
    # 根据截图类型执行不同操作
    if screenshot_type == "1":
        # 可视区域截图
        print(f"\n正在获取页面 {page_index} 的可视区域截图...")
        
        try:
            # 获取当前页面
            page = browser_tool.context.pages[page_index]
            
            # 获取截图
            result = browser_tool._async_loop.run_until_complete(
                page.screenshot(path=file_path, full_page=False)
            )
            
            print(f"截图已保存至: {file_path}")
            
        except Exception as e:
            print(f"获取截图失败: {str(e)}")
            
    elif screenshot_type == "2":
        # 完整页面截图
        print(f"\n正在获取页面 {page_index} 的完整页面截图...")
        
        try:
            # 获取当前页面
            page = browser_tool.context.pages[page_index]
            
            # 获取截图
            result = browser_tool._async_loop.run_until_complete(
                page.screenshot(path=file_path, full_page=True)
            )
            
            print(f"完整页面截图已保存至: {file_path}")
            
        except Exception as e:
            print(f"获取完整页面截图失败: {str(e)}")
            
    elif screenshot_type == "3":
        # 元素截图
        location_type = "1"  # 默认使用CSS选择器
        
        if element_selector and location_type == "1":
            # 通过CSS选择器
            if not element_selector:
                print("错误: 必须提供元素选择器")
                return
                
            # 默认不需要滚动截图
            scroll_capture = False
                
            print(f"\n正在获取页面 {page_index} 中元素 '{element_selector}' 的截图...")
            
            try:
                # 获取当前页面
                page = browser_tool.context.pages[page_index]
                
                # 查找元素
                element = browser_tool._async_loop.run_until_complete(
                    page.query_selector(element_selector)
                )
                
                if not element:
                    print(f"未找到元素: {element_selector}")
                    return
                
                if scroll_capture:
                    # 使用JavaScript获取元素的完整大小和内容
                    print("正在准备滚动截图...")
                    
                    # 获取元素的位置和大小
                    bbox = browser_tool._async_loop.run_until_complete(
                        element.bounding_box()
                    )
                    
                    if not bbox:
                        print("无法获取元素位置和大小，使用标准截图")
                        result = browser_tool._async_loop.run_until_complete(
                            element.screenshot(path=file_path)
                        )
                        print(f"元素截图已保存至: {file_path}")
                        return
                    
                    # 检查元素是否过大以及是否有滚动条
                    has_scroll = browser_tool._async_loop.run_until_complete(
                        page.evaluate(f"""
                            (selector) => {{
                                const el = document.querySelector(selector);
                                if (!el) return false;
                                
                                // 检查是否有滚动条
                                const style = window.getComputedStyle(el);
                                const hasVerticalScroll = el.scrollHeight > el.clientHeight;
                                const hasHorizontalScroll = el.scrollWidth > el.clientWidth;
                                const isScrollable = style.overflow === 'scroll' || 
                                                   style.overflow === 'auto' || 
                                                   style.overflowY === 'scroll' || 
                                                   style.overflowY === 'auto' ||
                                                   style.overflowX === 'scroll' || 
                                                   style.overflowX === 'auto';
                                
                                return (hasVerticalScroll || hasHorizontalScroll) && isScrollable;
                            }}
                        """, element_selector)
                    )
                    
                    if has_scroll:
                        print("检测到元素有滚动内容，正在执行滚动截图...")
                        
                        # 创建一个临时画布用于组合滚动截图
                        result = browser_tool._async_loop.run_until_complete(
                            page.evaluate(f"""
                                async (selector) => {{
                                    const el = document.querySelector(selector);
                                    if (!el) return {{ success: false, message: "无法找到元素" }};
                                    
                                    // 获取元素的完整尺寸
                                    const rect = el.getBoundingClientRect();
                                    const fullWidth = Math.max(el.scrollWidth, rect.width);
                                    const fullHeight = Math.max(el.scrollHeight, rect.height);
                                    
                                    // 如果元素尺寸不大，则不需要滚动截图
                                    if (fullWidth <= rect.width && fullHeight <= rect.height) {{
                                        return {{ 
                                            success: false, 
                                            message: "元素尺寸不大，不需要滚动截图",
                                            needScroll: false
                                        }};
                                    }}
                                    
                                    // 准备滚动参数
                                    el.style.scrollBehavior = 'auto'; // 禁用平滑滚动以加快速度
                                    
                                    // 记录原始滚动位置
                                    const originalScrollTop = el.scrollTop;
                                    const originalScrollLeft = el.scrollLeft;

                                    try {{
                                        // 滚动到左上角
                                        el.scrollTo(0, 0);
                                        
                                        return {{ 
                                            success: true, 
                                            fullWidth, 
                                            fullHeight,
                                            needScroll: true,
                                            originalScrollTop,
                                            originalScrollLeft
                                        }};
                                    }} catch (e) {{
                                        // 恢复原始滚动位置
                                        el.scrollTo(originalScrollLeft, originalScrollTop);
                                        return {{ 
                                            success: false, 
                                            message: "滚动操作失败: " + e.message,
                                            needScroll: false
                                        }};
                                    }}
                                }}
                            """, element_selector)
                        )
                        
                        if result.get('success', False) and result.get('needScroll', False):
                            full_width = result.get('fullWidth')
                            full_height = result.get('fullHeight')
                            original_scroll_top = result.get('originalScrollTop')
                            original_scroll_left = result.get('originalScrollLeft')
                            
                            print(f"元素完整尺寸: {full_width}x{full_height}px")
                            
                            # 使用元素直接截图，使用Playwright的内置功能
                            try:
                                # 执行截图
                                result = browser_tool._async_loop.run_until_complete(
                                    element.screenshot(path=file_path)
                                )
                                
                                print(f"元素滚动截图已保存至: {file_path}")
                                
                                # 恢复原始滚动位置
                                browser_tool._async_loop.run_until_complete(
                                    page.evaluate(f"""
                                        (selector, scrollLeft, scrollTop) => {{
                                            const el = document.querySelector(selector);
                                            if (el) {{
                                                el.scrollTo(scrollLeft, scrollTop);
                                            }}
                                        }}
                                    """, element_selector, original_scroll_left, original_scroll_top)
                                )
                            except Exception as scroll_err:
                                print(f"滚动截图过程中出错: {str(scroll_err)}")
                                print("尝试使用普通截图方法...")
                                
                                # 恢复原始滚动位置
                                browser_tool._async_loop.run_until_complete(
                                    page.evaluate(f"""
                                        (selector, scrollLeft, scrollTop) => {{
                                            const el = document.querySelector(selector);
                                            if (el) {{
                                                el.scrollTo(scrollLeft, scrollTop);
                                            }}
                                        }}
                                    """, element_selector, original_scroll_left, original_scroll_top)
                                )
                                
                                # 退回到普通截图
                                result = browser_tool._async_loop.run_until_complete(
                                    element.screenshot(path=file_path)
                                )
                                print(f"元素截图已保存至: {file_path}")
                        else:
                            print(f"滚动截图准备失败: {result.get('message', '未知错误')}")
                            print("使用普通截图方法...")
                            result = browser_tool._async_loop.run_until_complete(
                                element.screenshot(path=file_path)
                            )
                            print(f"元素截图已保存至: {file_path}")
                    else:
                        print("元素不可滚动或无滚动内容，使用普通截图")
                        result = browser_tool._async_loop.run_until_complete(
                            element.screenshot(path=file_path)
                        )
                        print(f"元素截图已保存至: {file_path}")
                else:
                    # 普通截图
                    result = browser_tool._async_loop.run_until_complete(
                        element.screenshot(path=file_path)
                    )
                    print(f"元素截图已保存至: {file_path}")
                
            except Exception as e:
                print(f"获取元素截图失败: {str(e)}")
            
            # 截图后显示相关信息
            try:
                # 获取元素的尺寸信息
                bbox = browser_tool._async_loop.run_until_complete(
                    element.bounding_box()
                )
                if bbox:
                    print(f"元素位置: x={bbox['x']:.0f}, y={bbox['y']:.0f}, 宽={bbox['width']:.0f}, 高={bbox['height']:.0f}")
                    
                # 获取元素是否在可视区域
                is_visible = browser_tool._async_loop.run_until_complete(
                    element.is_visible()
                )
                print(f"元素在可视区域: {'是' if is_visible else '否'}")
            except Exception:
                pass
        
        elif class_name and location_type == "2":
            # 通过类名查找
            if not class_name:
                print("错误: 必须提供类名")
                return
            
            # 默认设置
            exact_match = True
            include_iframes = True
            scroll_capture = False
            
            print(f"\n正在查找并截图类名为 '{class_name}' 的元素...")
            print(f"精确匹配: {'是' if exact_match else '否'}")
            print(f"包含iframe: {'是' if include_iframes else '否'}")
            print(f"滚动截图: {'是' if scroll_capture else '否'}")
            
            try:
                # 获取当前页面
                page = browser_tool.context.pages[page_index]
                
                # 构造选择器
                if exact_match:
                    # 精确匹配：必须完全匹配整个类名
                    selector = f".{class_name}"
                else:
                    # 部分匹配：包含该类名即可
                    selector = f"[class*='{class_name}']"
                
                # 记录已找到的元素
                found_elements = []
                
                # 在主页面中查找元素
                print("在主页面中查找元素...")
                main_elements = browser_tool._async_loop.run_until_complete(
                    page.query_selector_all(selector)
                )
                
                for i, elem in enumerate(main_elements):
                    is_visible = browser_tool._async_loop.run_until_complete(
                        elem.is_visible()
                    )
                    if is_visible:
                        elem_text = browser_tool._async_loop.run_until_complete(
                            page.evaluate("(el) => el.innerText || el.textContent || ''", elem)
                        )
                        elem_tag = browser_tool._async_loop.run_until_complete(
                            page.evaluate("(el) => el.tagName", elem)
                        )
                        
                        # 获取实际类名
                        elem_class = browser_tool._async_loop.run_until_complete(
                            page.evaluate("(el) => el.className", elem)
                        )
                        
                        # 获取位置信息
                        bbox = browser_tool._async_loop.run_until_complete(
                            elem.bounding_box()
                        )
                        
                        found_elements.append({
                            'element': elem,
                            'text': elem_text[:50] + ('...' if len(elem_text) > 50 else ''),
                            'tag': elem_tag,
                            'class': elem_class,
                            'from_iframe': False,
                            'bbox': bbox,
                            'selector': selector
                        })
                
                # 如果需要，在iframe中查找
                if include_iframes:
                    print("在iframe中查找元素...")
                    
                    # 获取所有iframe
                    iframe_handles = browser_tool._async_loop.run_until_complete(
                        page.query_selector_all('iframe')
                    )
                    
                    if iframe_handles:
                        print(f"找到 {len(iframe_handles)} 个iframe")
                        
                        for i, iframe_handle in enumerate(iframe_handles):
                            try:
                                # 获取iframe信息
                                iframe_id = browser_tool._async_loop.run_until_complete(
                                    iframe_handle.get_attribute('id')
                                ) or f"iframe_{i}"
                                
                                iframe_name = browser_tool._async_loop.run_until_complete(
                                    iframe_handle.get_attribute('name')
                                ) or iframe_id
                                
                                # 获取iframe内容框架
                                content_frame = browser_tool._async_loop.run_until_complete(
                                    iframe_handle.content_frame()
                                )
                                
                                if content_frame:
                                    print(f"搜索iframe: {iframe_name}")
                                    
                                    # 在iframe中查找元素
                                    iframe_elements = browser_tool._async_loop.run_until_complete(
                                        content_frame.query_selector_all(selector)
                                    )
                                    
                                    for j, iframe_elem in enumerate(iframe_elements):
                                        is_visible = browser_tool._async_loop.run_until_complete(
                                            iframe_elem.is_visible()
                                        )
                                        
                                        if is_visible:
                                            iframe_elem_text = browser_tool._async_loop.run_until_complete(
                                                content_frame.evaluate("(el) => el.innerText || el.textContent || ''", iframe_elem)
                                            )
                                            
                                            iframe_elem_tag = browser_tool._async_loop.run_until_complete(
                                                content_frame.evaluate("(el) => el.tagName", iframe_elem)
                                            )
                                            
                                            # 获取实际类名
                                            iframe_elem_class = browser_tool._async_loop.run_until_complete(
                                                content_frame.evaluate("(el) => el.className", iframe_elem)
                                            )
                                            
                                            # 获取位置信息
                                            iframe_bbox = browser_tool._async_loop.run_until_complete(
                                                iframe_elem.bounding_box()
                                            )
                                            
                                            found_elements.append({
                                                'element': iframe_elem,
                                                'text': iframe_elem_text[:50] + ('...' if len(iframe_elem_text) > 50 else ''),
                                                'tag': iframe_elem_tag,
                                                'class': iframe_elem_class,
                                                'from_iframe': True,
                                                'iframe_handle': iframe_handle,
                                                'iframe_index': i,
                                                'iframe_name': iframe_name,
                                                'content_frame': content_frame,
                                                'bbox': iframe_bbox,
                                                'selector': selector
                                            })
                            except Exception as iframe_err:
                                print(f"处理iframe '{iframe_name}' 时出错: {str(iframe_err)}")
                
                # 显示找到的元素
                if not found_elements:
                    print(f"未找到类名为 '{class_name}' 的元素")
                    return
                
                print(f"\n共找到 {len(found_elements)} 个元素:")
                for i, elem_info in enumerate(found_elements):
                    iframe_text = f" [在iframe: {elem_info['iframe_name']}]" if elem_info.get('from_iframe') else ""
                    position_text = ""
                    if elem_info.get('bbox'):
                        bbox = elem_info['bbox']
                        position_text = f" 位置: x={bbox['x']:.0f}, y={bbox['y']:.0f}, " \
                                        f"宽={bbox['width']:.0f}, 高={bbox['height']:.0f}"
                    
                    print(f"[{i+1}] <{elem_info['tag']}> 类名: '{elem_info['class']}'{iframe_text}")
                    print(f"    文本: {elem_info['text']}{position_text}")
                
                # 默认选择第一个元素
                element_index = 0  # 选择第一个找到的元素
                
                if element_index >= len(found_elements):
                    print("未找到有效元素")
                    return
                    
                # 获取选中的元素
                selected_element_info = found_elements[element_index]
                selected_element = selected_element_info['element']
                from_iframe = selected_element_info.get('from_iframe', False)
                
                print(f"\n正在截图选中的元素...")
                
                if scroll_capture:
                    print("使用滚动截图功能...")
                    
                # 进行截图
                try:
                    if from_iframe:
                        print(f"正在获取iframe中的元素截图...")
                        
                        # 获取iframe中的元素
                        content_frame = selected_element_info['content_frame']
                        
                        # 尝试先滚动元素到可见区域
                        browser_tool._async_loop.run_until_complete(
                            content_frame.evaluate("""
                                (el) => {
                                    el.scrollIntoView({behavior: 'auto', block: 'center'});
                                    return new Promise(resolve => setTimeout(resolve, 500));
                                }
                            """, selected_element)
                        )
                        
                        # 尝试截图
                        try:
                            browser_tool._async_loop.run_until_complete(
                                selected_element.screenshot(path=file_path, timeout=5000)
                            )
                            print(f"元素截图已保存至: {file_path}")
                        except Exception as e:
                            print(f"元素截图失败: {str(e)}")
                            print("正在尝试页面截图...")
                            
                            # 使用全页面截图作为备选
                            browser_tool._async_loop.run_until_complete(
                                browser_tool.context.pages[page_index].screenshot(path=file_path, full_page=True)
                            )
                            print(f"全页面截图已保存至: {file_path}")
                    else:
                        # 主页面中的元素
                        try:
                            # 尝试先滚动元素到可见区域
                            browser_tool._async_loop.run_until_complete(
                                page.evaluate("""
                                    (el) => {
                                        el.scrollIntoView({behavior: 'auto', block: 'center'});
                                        return new Promise(resolve => setTimeout(resolve, 500));
                                    }
                                """, selected_element)
                            )
                            
                            browser_tool._async_loop.run_until_complete(
                                selected_element.screenshot(path=file_path)
                            )
                            print(f"元素截图已保存至: {file_path}")
                        except Exception as e:
                            print(f"元素截图失败: {str(e)}")
                            print("正在尝试页面截图...")
                            
                            # 使用全页面截图作为备选
                            browser_tool._async_loop.run_until_complete(
                                page.screenshot(path=file_path, full_page=True)
                            )
                            print(f"全页面截图已保存至: {file_path}")
                    
                    # 显示截图信息
                    bbox = selected_element_info.get('bbox', {})
                    if bbox:
                        print(f"元素位置: x={bbox['x']:.0f}, y={bbox['y']:.0f}, 宽={bbox['width']:.0f}, 高={bbox['height']:.0f}")
                    
                except Exception as screenshot_err:
                    print(f"截图过程中出错: {str(screenshot_err)}")
                    
                    # 最后的备选方案：整页截图
                    try:
                        browser_tool._async_loop.run_until_complete(
                            browser_tool.context.pages[page_index].screenshot(path=file_path, full_page=True)
                        )
                        print(f"已保存整个页面的截图: {file_path}")
                    except Exception as final_err:
                        print(f"全页面截图失败: {str(final_err)}")
            except Exception as e:
                print(f"查找或截图元素失败: {str(e)}")
                return
                
        elif search_text and location_type == "3":
            # 通过文本内容查找
            if not search_text:
                print("错误: 必须提供搜索文本")
                return
                
            # 默认不需要滚动截图
            scroll_capture = False
            
            # 其余代码保持不变
                
    elif screenshot_type == "4":
        # 滚动截图 - 基于JS控制滚动并拼接图片
        print(f"\n正在对页面 {page_index} 执行滚动截图...")
        
        try:
            # 获取当前页面
            page = browser_tool.context.pages[page_index]
            
            # 设置是否截取特定元素
            capture_element = element_selector is not None
            scroll_element = None
            
            if capture_element:
                if not element_selector:
                    print("未提供有效的选择器，将截取整个页面")
                    capture_element = False
                else:
                    # 默认不在iframe中查找
                    check_iframe = False
                    in_iframe = False
                    content_frame = None
                    selected_iframe = None
                    
                    if check_iframe:
                        # 查找所有iframe
                        iframe_handles = browser_tool._async_loop.run_until_complete(
                            page.query_selector_all('iframe')
                        )
                        
                        if iframe_handles:
                            print(f"\n找到 {len(iframe_handles)} 个iframe")
                            
                            # 获取iframe信息
                            iframe_info = []
                            for i, iframe in enumerate(iframe_handles):
                                try:
                                    iframe_id = browser_tool._async_loop.run_until_complete(
                                        iframe.get_attribute('id')
                                    ) or f"iframe_{i}"
                                    
                                    iframe_name = browser_tool._async_loop.run_until_complete(
                                        iframe.get_attribute('name')
                                    ) or iframe_id
                                    
                                    iframe_info.append({
                                        'index': i,
                                        'id': iframe_id,
                                        'name': iframe_name,
                                        'handle': iframe
                                    })
                                except:
                                    pass
                            
                            # 显示iframe列表
                            for i, info in enumerate(iframe_info):
                                print(f"[{i+1}] {info['name']} (id: {info['id']})")
                            
                            # 默认选择第一个iframe
                            try:
                                iframe_index = 0  # 选择第一个iframe
                                if 0 <= iframe_index < len(iframe_info):
                                    selected_iframe = iframe_info[iframe_index]['handle']
                                    
                                    # 获取iframe内容
                                    content_frame = browser_tool._async_loop.run_until_complete(
                                        selected_iframe.content_frame()
                                    )
                                    
                                    if content_frame:
                                        # 尝试在iframe中查找元素
                                        scroll_element = browser_tool._async_loop.run_until_complete(
                                            content_frame.query_selector(element_selector)
                                        )
                                        
                                        if scroll_element:
                                            print(f"在iframe中找到元素: {element_selector}")
                                            in_iframe = True
                                            
                                            # 将iframe滚动到视图中
                                            browser_tool._async_loop.run_until_complete(
                                                page.evaluate("""
                                                    (index) => {
                                                        const iframe = document.querySelectorAll('iframe')[index];
                                                        if (iframe) {
                                                            iframe.scrollIntoView({behavior: 'auto', block: 'start'});
                                                            return new Promise(resolve => setTimeout(resolve, 800));
                                                        }
                                                    }
                                                """, iframe_index)
                                            )
                                            
                                            print("\n正在准备对iframe中的元素进行滚动截图...")
                                        else:
                                            print(f"未在iframe中找到元素: {element_selector}")
                                            capture_element = False
                                    else:
                                        print("无法访问iframe内容")
                                        capture_element = False
                                else:
                                    print("选择的iframe序号无效")
                                    capture_element = False
                            except:
                                print("选择无效，将截取整个页面")
                                capture_element = False
                        else:
                            print("页面中没有找到iframe")
                            capture_element = False
                    else:
                        # 在主页面中查找元素
                        scroll_element = browser_tool._async_loop.run_until_complete(
                            page.query_selector(element_selector)
                        )
                        
                        if not scroll_element:
                            print(f"未找到元素: {element_selector}，将截取整个页面")
                            capture_element = False
            
            # 准备临时文件路径
            timestamp = int(time.time())
            temp_dir = os.path.dirname(file_path)
            base_filename = os.path.splitext(os.path.basename(file_path))[0]
            extension = os.path.splitext(file_path)[1] or '.png'
            
            # 获取屏幕尺寸和滚动信息
            page_info = browser_tool._async_loop.run_until_complete(
                page.evaluate("""
                    (selector) => {
                        const target = selector ? document.querySelector(selector) : document.documentElement;
                        if (!target) return null;
                        
                        const rect = target.getBoundingClientRect();
                        
                        return {
                            scrollHeight: target.scrollHeight,
                            scrollWidth: target.scrollWidth,
                            clientHeight: target.clientHeight || window.innerHeight,
                            clientWidth: target.clientWidth || window.innerWidth,
                            hasScroll: target.scrollHeight > (target.clientHeight || window.innerHeight)
                        };
                    }
                """, element_selector if capture_element else None)
            )
            
            if not page_info:
                print("无法获取页面信息，将使用标准截图")
                browser_tool._async_loop.run_until_complete(
                    page.screenshot(path=file_path, full_page=True)
                )
                print(f"页面截图已保存至: {file_path}")
                return
            
            scroll_height = page_info.get('scrollHeight', 0)
            client_height = page_info.get('clientHeight', 0)
            has_scroll = page_info.get('hasScroll', False)
            
            print(f"页面尺寸: 总高度 {scroll_height}px, 可见高度 {client_height}px")
            
            if not has_scroll:
                print("页面无需滚动，直接截取完整页面")
                if capture_element and scroll_element:
                    browser_tool._async_loop.run_until_complete(
                        scroll_element.screenshot(path=file_path)
                    )
                else:
                    browser_tool._async_loop.run_until_complete(
                        page.screenshot(path=file_path, full_page=True)
                    )
                print(f"页面截图已保存至: {file_path}")
                return
            
            # 计算需要滚动的次数
            if client_height <= 0:
                client_height = 600  # 默认值
            
            step_size = int(client_height * 0.8)  # 每次滚动80%的可见高度，确保有重叠
            steps = max(1, int(scroll_height / step_size))
            
            print(f"需要滚动 {steps} 次来捕获完整内容")
            
            # 准备存储每一帧的文件路径
            frame_paths = []
            
            # 先滚动到顶部
            browser_tool._async_loop.run_until_complete(
                page.evaluate("""
                    (selector) => {
                        const target = selector ? document.querySelector(selector) : window;
                        target.scrollTo(0, 0);
                        return new Promise(resolve => setTimeout(resolve, 800));
                    }
                """, element_selector if capture_element else None)
            )
            
            # 逐步滚动并截图
            for i in range(steps + 1):  # +1 确保捕获底部
                current_scroll = i * step_size
                
                # 滚动到指定位置
                browser_tool._async_loop.run_until_complete(
                    page.evaluate("""
                        (scrollTop, selector) => {
                            const target = selector ? document.querySelector(selector) : window;
                            target.scrollTo(0, scrollTop);
                            return new Promise(resolve => setTimeout(resolve, 500));
                        }
                    """, current_scroll, element_selector if capture_element else None)
                )
                
                # 生成当前帧的文件路径
                frame_path = os.path.join(temp_dir, f"{base_filename}_frame_{i}{extension}")
                
                # 截取当前可见区域
                if capture_element and scroll_element:
                    try:
                        if in_iframe:
                            # 对iframe内的元素使用特殊处理
                            try:
                                # 确保iframe内的滚动位置正确
                                browser_tool._async_loop.run_until_complete(
                                    content_frame.evaluate("""
                                        (scrollTop) => {
                                            window.scrollTo(0, scrollTop);
                                            return new Promise(resolve => setTimeout(resolve, 300));
                                        }
                                    """, current_scroll)
                                )
                                
                                # 尝试对元素本身截图
                                browser_tool._async_loop.run_until_complete(
                                    scroll_element.screenshot(path=frame_path)
                                )
                            except Exception as iframe_err:
                                print(f"iframe内元素截图失败: {str(iframe_err)}")
                                
                                # 尝试截取整个iframe
                                try:
                                    browser_tool._async_loop.run_until_complete(
                                        selected_iframe.screenshot(path=frame_path)
                                    )
                                except Exception as iframe_element_err:
                                    print(f"iframe截图失败: {str(iframe_element_err)}")
                                    browser_tool._async_loop.run_until_complete(
                                        page.screenshot(path=frame_path)
                                    )
                        else:
                            # 普通元素截图
                            browser_tool._async_loop.run_until_complete(
                                scroll_element.screenshot(path=frame_path)
                            )
                    except Exception as e:
                        print(f"元素截图失败: {str(e)}，使用页面截图替代")
                        browser_tool._async_loop.run_until_complete(
                            page.screenshot(path=frame_path)
                        )
                else:
                    browser_tool._async_loop.run_until_complete(
                        page.screenshot(path=frame_path)
                    )
                
                frame_paths.append(frame_path)
                print(f"已捕获第 {i+1}/{steps+1} 帧")
            
            # 拼接所有帧
            if len(frame_paths) > 1:
                print("\n正在拼接截图...")
                images_stitch(frame_paths, file_path, 'vertical')
                
                # 清理临时文件
                for frame_path in frame_paths:
                    try:
                        os.remove(frame_path)
                    except:
                        pass
                
                print(f"滚动截图已完成并保存至: {file_path}")
            else:
                # 只有一帧，直接使用
                if os.path.exists(frame_paths[0]):
                    try:
                        os.rename(frame_paths[0], file_path)
                    except:
                        import shutil
                        shutil.copy2(frame_paths[0], file_path)
                        os.remove(frame_paths[0])
                    print(f"单帧截图已保存至: {file_path}")
            
        except Exception as e:
            print(f"滚动截图过程中出错: {str(e)}")
            
            # 尝试标准截图作为备选
            try:
                print("使用标准截图方法...")
                browser_tool._async_loop.run_until_complete(
                    page.screenshot(path=file_path, full_page=True)
                )
                print(f"页面截图已保存至: {file_path}")
            except Exception as backup_err:
                print(f"截图完全失败: {str(backup_err)}")
                return
    elif screenshot_type == "5":
        # PDF查看器截图
        print(f"\n正在对页面 {page_index} 执行PDF查看器截图...")
        
        try:
            # 获取当前页面
            page = browser_tool.context.pages[page_index]
            
            # 设置PDF查看器的默认选择器
            container_selector = "#viewerContainer"
            viewer_selector = "#viewer"
            page_selector = ".page"
            
            # 默认不在iframe中查找
            in_iframe = False
            selected_iframe = None
            content_frame = None
            
            if in_iframe:
                # 查找所有iframe
                iframe_handles = browser_tool._async_loop.run_until_complete(
                    page.query_selector_all('iframe')
                )
                
                if not iframe_handles:
                    print("页面中未找到iframe，将在主页面查找PDF查看器")
                    in_iframe = False
                else:
                    print(f"\n找到 {len(iframe_handles)} 个iframe")
                    
                    # 获取iframe信息
                    iframe_info = []
                    for i, iframe in enumerate(iframe_handles):
                        try:
                            iframe_id = browser_tool._async_loop.run_until_complete(
                                iframe.get_attribute('id')
                            ) or f"iframe_{i}"
                            
                            iframe_name = browser_tool._async_loop.run_until_complete(
                                iframe.get_attribute('name')
                            ) or iframe_id
                            
                            iframe_info.append({
                                'index': i,
                                'id': iframe_id,
                                'name': iframe_name,
                                'handle': iframe
                            })
                        except Exception as e:
                            print(f"获取iframe {i} 信息时出错: {str(e)}")
                    
                    # 显示iframe列表
                    for i, info in enumerate(iframe_info):
                        print(f"[{i+1}] {info['name']} (id: {info['id']})")
                    
                    # 默认选择第一个iframe
                    try:
                        iframe_index = 0  # 选择第一个iframe
                        if 0 <= iframe_index < len(iframe_info):
                            selected_iframe = iframe_info[iframe_index]['handle']
                            
                            # 获取iframe内容
                            content_frame = browser_tool._async_loop.run_until_complete(
                                selected_iframe.content_frame()
                            )
                            
                            if not content_frame:
                                print("无法访问iframe内容，将在主页面查找PDF查看器")
                                in_iframe = False
                            else:
                                print(f"已选择iframe: {iframe_info[iframe_index]['name']}")
                                
                                # 将iframe滚动到视图中
                                browser_tool._async_loop.run_until_complete(
                                    page.evaluate("""
                                        (index) => {
                                            const iframe = document.querySelectorAll('iframe')[index];
                                            if (iframe) {
                                                iframe.scrollIntoView({behavior: 'auto', block: 'start'});
                                                return new Promise(resolve => setTimeout(resolve, 800));
                                            }
                                        }
                                    """, iframe_index)
                                )
                    except Exception as e:
                        print(f"选择iframe时出错: {str(e)}，将在主页面查找PDF查看器")
                        in_iframe = False
            
            # 准备临时文件路径
            timestamp = int(time.time())
            temp_dir = os.path.dirname(file_path)
            base_filename = os.path.splitext(os.path.basename(file_path))[0]
            extension = os.path.splitext(file_path)[1] or '.png'
            
            # 获取页面数量和信息
            if in_iframe and content_frame:
                # 在iframe中查找PDF查看器
                page_info = browser_tool._async_loop.run_until_complete(
                    content_frame.evaluate("""
                        (params) => {
                            const containerSelector = params.containerSelector;
                            const viewerSelector = params.viewerSelector;
                            const pageSelector = params.pageSelector;
                            
                            const container = document.querySelector(containerSelector);
                            if (!container) return { success: false, message: "未在iframe中找到容器元素" };
                            
                            const viewer = document.querySelector(viewerSelector);
                            if (!viewer) return { success: false, message: "未在iframe中找到查看器元素" };
                            
                            const pages = document.querySelectorAll(pageSelector);
                            if (!pages || pages.length === 0) return { success: false, message: "未在iframe中找到页面元素" };
                            
                            const pagesInfo = [];
                            let totalHeight = 0;
                            
                            for (let i = 0; i < pages.length; i++) {
                                const page = pages[i];
                                const rect = page.getBoundingClientRect();
                                const pageNumber = page.getAttribute('data-page-number') || (i + 1);
                                
                                pagesInfo.push({
                                    index: i,
                                    pageNumber: pageNumber,
                                    width: rect.width,
                                    height: rect.height,
                                    top: rect.top,
                                    left: rect.left
                                });
                                
                                totalHeight += rect.height;
                            }
                            
                            return {
                                success: true,
                                pageCount: pages.length,
                                pagesInfo: pagesInfo,
                                containerRect: container.getBoundingClientRect(),
                                viewerRect: viewer.getBoundingClientRect(),
                                totalHeight: totalHeight
                            };
                        }
                    """, { 'containerSelector': container_selector, 'viewerSelector': viewer_selector, 'pageSelector': page_selector })
                )
            else:
                # 在主页面查找PDF查看器
                page_info = browser_tool._async_loop.run_until_complete(
                    page.evaluate("""
                        (params) => {
                            const containerSelector = params.containerSelector;
                            const viewerSelector = params.viewerSelector;
                            const pageSelector = params.pageSelector;
                            
                            const container = document.querySelector(containerSelector);
                            if (!container) return { success: false, message: "未找到容器元素" };
                            
                            const viewer = document.querySelector(viewerSelector);
                            if (!viewer) return { success: false, message: "未找到查看器元素" };
                            
                            const pages = document.querySelectorAll(pageSelector);
                            if (!pages || pages.length === 0) return { success: false, message: "未找到页面元素" };
                            
                            const pagesInfo = [];
                            let totalHeight = 0;
                            
                            for (let i = 0; i < pages.length; i++) {
                                const page = pages[i];
                                const rect = page.getBoundingClientRect();
                                const pageNumber = page.getAttribute('data-page-number') || (i + 1);
                                
                                pagesInfo.push({
                                    index: i,
                                    pageNumber: pageNumber,
                                    width: rect.width,
                                    height: rect.height,
                                    top: rect.top,
                                    left: rect.left
                                });
                                
                                totalHeight += rect.height;
                            }
                            
                            return {
                                success: true,
                                pageCount: pages.length,
                                pagesInfo: pagesInfo,
                                containerRect: container.getBoundingClientRect(),
                                viewerRect: viewer.getBoundingClientRect(),
                                totalHeight: totalHeight
                            };
                        }
                    """, { 'containerSelector': container_selector, 'viewerSelector': viewer_selector, 'pageSelector': page_selector })
                )
            
            if not page_info.get('success', False):
                print(f"获取PDF查看器信息失败: {page_info.get('message', '未知错误')}")
                return
            
            page_count = page_info.get('pageCount', 0)
            pages_info = page_info.get('pagesInfo', [])
            
            location_text = "iframe中" if in_iframe else "主页面中"
            print(f"在{location_text}检测到 {page_count} 个PDF页面")
            
            if page_count == 0:
                print("未检测到有效的PDF页面")
                return
            
            # 创建临时目录存储各页截图
            os.makedirs(temp_dir, exist_ok=True)
            frame_paths = []
            
            # 逐页截图
            for i, page_info in enumerate(pages_info):
                page_number = page_info.get('pageNumber', i+1)
                print(f"正在截取第 {page_number} 页 ({i+1}/{page_count})...")
                
                # 滚动到当前页面
                if in_iframe and content_frame:
                    browser_tool._async_loop.run_until_complete(
                        content_frame.evaluate("""
                            (params) => {
                                const pageSelector = params.pageSelector;
                                const index = params.index;
                                
                                const pages = document.querySelectorAll(pageSelector);
                                if (pages && pages[index]) {
                                    pages[index].scrollIntoView({behavior: 'auto', block: 'center'});
                                    return new Promise(resolve => setTimeout(resolve, 300));
                                }
                            }
                        """, { 'pageSelector': page_selector, 'index': i })
                    )
                else:
                    browser_tool._async_loop.run_until_complete(
                        page.evaluate("""
                            (params) => {
                                const pageSelector = params.pageSelector;
                                const index = params.index;
                                
                                const pages = document.querySelectorAll(pageSelector);
                                if (pages && pages[index]) {
                                    pages[index].scrollIntoView({behavior: 'auto', block: 'center'});
                                    return new Promise(resolve => setTimeout(resolve, 300));
                                }
                            }
                        """, { 'pageSelector': page_selector, 'index': i })
                    )
                
                # 截取当前页
                frame_path = os.path.join(temp_dir, f"{base_filename}_page_{i+1}{extension}")
                
                # 使用page选择器找到特定页面元素
                current_page_selector = f"{page_selector}[data-page-number='{page_number}']"
                if not page_info.get('pageNumber'):
                    # 如果没有pageNumber属性，使用索引
                    current_page_selector = f"{page_selector}:nth-of-type({i+1})"
                
                print(f"使用选择器: {current_page_selector}")
                
                # 根据是否在iframe中，使用不同的截图方法
                if in_iframe and content_frame:
                    # 在iframe中查找元素并截图
                    page_element = browser_tool._async_loop.run_until_complete(
                        content_frame.query_selector(current_page_selector)
                    )
                    
                    if not page_element:
                        print(f"无法在iframe中找到第 {page_number} 页元素，尝试使用备用方法...")
                        
                        # 备用方法：使用JavaScript查找元素
                        js_result = browser_tool._async_loop.run_until_complete(
                            content_frame.evaluate("""
                                (params) => {
                                    const selector = params.selector;
                                    const element = document.querySelector(selector);
                                    return element ? true : false;
                                }
                            """, { 'selector': current_page_selector })
                        )
                        
                        if not js_result:
                            print(f"无法在iframe中找到第 {page_number} 页元素，跳过该页")
                            continue
                        
                        # 尝试对整个iframe进行截图，后续处理
                        print("使用整个iframe截图代替...")
                        browser_tool._async_loop.run_until_complete(
                            selected_iframe.screenshot(path=frame_path)
                        )
                    else:
                        # 直接截取iframe中的页面元素
                        try:
                            browser_tool._async_loop.run_until_complete(
                                page_element.screenshot(path=frame_path)
                            )
                        except Exception as e:
                            print(f"iframe中元素截图失败: {str(e)}")
                            
                            # 尝试截取整个iframe作为备选
                            print("使用整个iframe截图代替...")
                            try:
                                browser_tool._async_loop.run_until_complete(
                                    selected_iframe.screenshot(path=frame_path)
                                )
                            except Exception as iframe_err:
                                print(f"iframe截图失败: {str(iframe_err)}")
                                continue
                else:
                    # 在主页面中查找元素并截图
                    page_element = browser_tool._async_loop.run_until_complete(
                        page.query_selector(current_page_selector)
                    )
                    
                    if not page_element:
                        print(f"无法找到第 {page_number} 页元素，尝试使用备用方法...")
                        
                        # 备用方法：使用JavaScript查找元素
                        js_result = browser_tool._async_loop.run_until_complete(
                            page.evaluate("""
                                (params) => {
                                    const selector = params.selector;
                                    const element = document.querySelector(selector);
                                    return element ? true : false;
                                }
                            """, { 'selector': current_page_selector })
                        )
                        
                        if not js_result:
                            print(f"无法找到第 {page_number} 页元素，跳过该页")
                            continue
                        
                        # 使用整个查看器截图，后续处理
                        print("使用整页截图代替...")
                        browser_tool._async_loop.run_until_complete(
                            page.screenshot(path=frame_path)
                        )
                    else:
                        # 直接截取页面元素
                        browser_tool._async_loop.run_until_complete(
                            page_element.screenshot(path=frame_path)
                        )
                
                frame_paths.append(frame_path)
                print(f"已截取第 {page_number} 页")
            
            # 拼接所有页面
            if len(frame_paths) > 0:
                print("\n正在拼接所有页面...")
                
                try:
                    images_stitch(frame_paths, file_path, 'vertical')
                    
                    # 清理临时文件
                    for frame_path in frame_paths:
                        try:
                            os.remove(frame_path)
                        except:
                            pass
                    
                    print(f"PDF查看器截图已完成并保存至: {file_path}")
                    
                except Exception as e:
                    print(f"拼接图片时出错: {str(e)}")
                    print("保留单页截图...")
                    
                    # 如果拼接失败，保留单页截图
                    print(f"单页截图已保存在: {temp_dir}")
            else:
                print("没有获取到任何PDF页面截图")
            
        except Exception as e:
            print(f"PDF查看器截图过程中出错: {str(e)}")
            
            # 尝试标准截图作为备选
            try:
                print("使用标准截图方法...")
                browser_tool._async_loop.run_until_complete(
                    page.screenshot(path=file_path, full_page=True)
                )
                print(f"页面截图已保存至: {file_path}")
            except Exception as backup_err:
                print(f"截图完全失败: {str(backup_err)}")
                return
    else:
        print("无效的截图类型选择")

    # 截图结束后询问是否分析图片
    analysis_result = None
    if os.path.exists(file_path):
        if auto_analysis:
            print("\n正在分析图片内容...")
            # 使用默认模板，不传递具体职位名称
            analysis_result = analysis_resume(file_path)
            
            # 分析完成后自动删除图片
            try:
                os.remove(file_path)
                print(f"分析完成，临时图片已删除")
            except Exception as del_err:
                print(f"删除临时图片失败: {str(del_err)}")
                
            # 显示分析结果
            print("\n分析结果:")
            print(json.dumps(analysis_result, ensure_ascii=False, indent=2))
        
    return {
        "file_path": file_path,
        "analysis_result": analysis_result
    }

# 添加图像拼接函数
def images_stitch(image_paths, output_path, direction='vertical'):
    """
    拼接多张图片
    :param image_paths: 图片路径列表
    :param output_path: 输出图片路径
    :param direction: 拼接方向，'vertical'垂直拼接，'horizontal'水平拼接
    :return: 输出图片路径
    """
    if not image_paths:
        return None
        
    # 打开所有图片
    images = [Image.open(img_path) for img_path in image_paths]
    
    if direction == 'vertical':
        # 垂直拼接（上下拼接）
        width = max(img.width for img in images)
        height = sum(img.height for img in images)
        
        # 创建新图片
        result = Image.new('RGB', (width, height))
        
        # 拼接图片
        current_height = 0
        for img in images:
            result.paste(img, (0, current_height))
            current_height += img.height
    else:
        # 水平拼接（左右拼接）
        width = sum(img.width for img in images)
        height = max(img.height for img in images)
        
        # 创建新图片
        result = Image.new('RGB', (width, height))
        
        # 拼接图片
        current_width = 0
        for img in images:
            result.paste(img, (current_width, 0))
            current_width += img.width
    
    # 保存结果
    result.save(output_path)
    return output_path