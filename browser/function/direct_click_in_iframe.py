import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))


# 导入依赖的函数
from .simplify_selector import simplify_selector
from .extract_tag_from_selector import extract_tag_from_selector
from .wait_and_get_page_info import wait_and_get_page_info


def direct_click_in_iframe(browser_tool, page_index, iframe_index, selector, wait_for_navigation=True):
    """
    直接在iframe中查找元素并执行点击
    
    Args:
        browser_tool: BrowserTool实例
        page_index: 页面索引
        iframe_index: iframe索引
        selector: 元素选择器
        wait_for_navigation: 是否等待导航
        
    Returns:
        dict: 包含点击结果的字典
    """
    result = {
        'success': False,
        'message': '',
        'title': '',
        'url': ''
    }
    
    try:
        # 1. 获取iframe句柄
        iframe_handles = browser_tool._async_loop.run_until_complete(
            browser_tool.context.pages[page_index].query_selector_all('iframe')
        )
        
        if iframe_index >= len(iframe_handles):
            result['message'] = f"找不到iframe (索引: {iframe_index})"
            return result
            
        iframe_handle = iframe_handles[iframe_index]
        
        # 2. 获取iframe内容框架
        content_frame = browser_tool._async_loop.run_until_complete(iframe_handle.content_frame())
        
        if not content_frame:
            result['message'] = "无法获取iframe内容框架"
            return result
            
        # 3. 查找元素
        element = browser_tool._async_loop.run_until_complete(
            content_frame.query_selector(selector)
        )
        
        if not element:
            # 尝试使用更简单的选择器
            simplified_selector = simplify_selector(selector)
            if simplified_selector != selector:
                print(f"原始选择器可能过于复杂，尝试简化选择器: {simplified_selector}")
                element = browser_tool._async_loop.run_until_complete(
                    content_frame.query_selector(simplified_selector)
                )
        
        if not element:
            # 如果仍然找不到元素，尝试直接使用标签类型
            tag_type = extract_tag_from_selector(selector)
            if tag_type:
                print(f"尝试使用标签类型选择器: {tag_type}")
                elements = browser_tool._async_loop.run_until_complete(
                    content_frame.query_selector_all(tag_type)
                )
                
                # 找到可见且可点击的元素
                for elem in elements:
                    is_visible = browser_tool._async_loop.run_until_complete(
                        elem.is_visible()
                    )
                    if is_visible:
                        element = elem
                        break
                        
        if not element:
            result['message'] = f"在iframe中未找到元素: {selector}"
            
            # 最后尝试JavaScript点击
            try:
                print("尝试使用JavaScript点击")
                js_clicked = browser_tool._async_loop.run_until_complete(
                    content_frame.evaluate(f"""
                    () => {{
                        try {{
                            // 1. 尝试选择器
                            let element = document.querySelector('{selector}');
                            
                            // 2. 如果没找到，尝试查找按钮
                            if (!element) {{
                                const buttons = Array.from(document.querySelectorAll('button'));
                                element = buttons.find(btn => btn.innerText && btn.innerText.includes('打招呼') || btn.innerText.includes('继续'));
                            }}
                            
                            // 3. 如果仍没找到，尝试查找任何可能的操作按钮
                            if (!element) {{
                                const clickables = Array.from(document.querySelectorAll('button, a, [role="button"], .btn, .button'));
                                element = clickables.find(el => 
                                    window.getComputedStyle(el).display !== 'none' && 
                                    window.getComputedStyle(el).visibility !== 'hidden'
                                );
                            }}
                            
                            if (element) {{
                                console.log('找到元素，执行点击');
                                element.click();
                                return true;
                            }}
                            
                            return false;
                        }} catch (e) {{
                            console.error('点击JS错误:', e);
                            return false;
                        }}
                    }}
                    """)
                )
                
                if js_clicked:
                    print("通过JavaScript成功执行点击")
                    wait_and_get_page_info(browser_tool, page_index, wait_for_navigation, result)
                    result['success'] = True
                    result['message'] = "通过JavaScript成功点击"
                    return result
            except Exception as js_err:
                print(f"JavaScript点击失败: {str(js_err)}")
            
            return result
            
        # 4. 执行点击
        print(f"在iframe中找到元素，执行点击...")
        browser_tool._async_loop.run_until_complete(element.click())
        
        # 5. 等待可能的导航并获取页面信息
        wait_and_get_page_info(browser_tool, page_index, wait_for_navigation, result)
        
        result['success'] = True
        result['message'] = "在iframe中成功点击元素"
        
    except Exception as e:
        result['success'] = False
        result['message'] = f"在iframe中点击元素时出错: {str(e)}"
    
    return result