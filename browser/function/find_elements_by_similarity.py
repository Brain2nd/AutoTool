import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))


# 导入依赖函数
from .direct_click_in_iframe import direct_click_in_iframe


def find_elements_by_similarity(browser_tool, page_index=None, search_text=None, 
                               element_types=None, similarity_threshold=None, 
                               max_results=None, include_iframes=None, 
                               auto_click=False, click_index=None, operation_type=None,
                               wait_for_navigation=None):
    """查找与文本相似的元素
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要查找元素的页面序号
        search_text: 要查找的文本
        element_types: 要查找的元素类型列表，例如['button','a','div']
        similarity_threshold: 相似度阈值，默认0.75
        max_results: 最大结果数，默认5
        include_iframes: 是否在iframe中查找元素，默认True
        auto_click: 是否自动点击找到的元素，默认False
        click_index: 要点击的元素索引（从1开始），如果auto_click为True时使用
        operation_type: 操作类型 ('1'=点击, '2'=双击, '3'=悬停, '4'=高亮)，默认'1'
        wait_for_navigation: 是否等待导航，默认True
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取要查询的页面序号
    if page_index is None:
        page_index = 0  # 默认使用第一个页面
        
    # 输入搜索文本
    if search_text is None:
        print("错误: 必须提供search_text参数")
        return
    
    # 选择是否限制元素类型
    if element_types is None:
        print("\n是否限制元素类型? (y/n, 默认否): ")
        # 在非交互模式下，默认不限制类型
        element_types = None
    
    # 设置相似度阈值
    if similarity_threshold is None:
        similarity_threshold = 0.75
    
    # 设置最大结果数
    if max_results is None:
        max_results = 5
    
    # 是否包含iframe中的元素
    if include_iframes is None:
        include_iframes = True
    
    print(f"\n正在查找与 '{search_text}' 相似的元素...")
    print(f"相似度阈值: {similarity_threshold}")
    print(f"最大结果数: {max_results}")
    print(f"元素类型: {', '.join(element_types) if element_types else '所有类型'}")
    print(f"包含iframe: {'是' if include_iframes else '否'}")
    
    result = browser_tool.find_elements_by_similarity(
        page_index, 
        search_text, 
        element_types, 
        similarity_threshold, 
        max_results,
        include_iframes
    )
    
    if not result['success']:
        print(f"查找元素失败: {result['message']}")
        return
    
    # 显示找到的元素
    elements = result['elements']
    similarities = result['similarities']
    
    if not elements:
        print(f"未找到与 '{search_text}' 相似的元素")
        return
    
    print(f"\n找到 {len(elements)} 个相似元素:")
    
    for i, (element, similarity) in enumerate(zip(elements, similarities)):
        # 判断元素是否来自iframe
        from_iframe = element.get('from_iframe', False)
        iframe_info = ""
        
        if from_iframe:
            iframe_name = element.get('iframe_name', 'unknown')
            iframe_id = element.get('iframe_id', 'unknown')
            iframe_info = f" [来自iframe: {iframe_name}]"
        
        # 构建元素描述
        element_type = element.get('type', 'unknown')
        element_text = element.get('text', '')
        element_value = element.get('value', '')
        element_aria = element.get('ariaLabel', '')
        element_title = element.get('title', '')
        
        # 组合显示文本
        display_text = element_text or element_value or element_aria or element_title or '(无文本)'
        if len(display_text) > 50:
            display_text = display_text[:47] + "..."
        
        print(f"[{i+1}] {element_type}: '{display_text}'{iframe_info}")
        print(f"    相似度: {similarity:.2f}")
        
        # 显示元素位置
        if 'rect' in element:
            rect = element['rect']
            print(f"    位置: x={rect['x']:.0f}, y={rect['y']:.0f}, 宽={rect['width']:.0f}, 高={rect['height']:.0f}")
        
        # 显示选择器信息
        if 'cssSelector' in element:
            selector = element['cssSelector']
            if len(selector) > 60:
                selector = selector[:57] + "..."
            print(f"    选择器: {selector}")
        
        # 如果是iframe内的元素，显示iframe相关信息
        if from_iframe and 'iframe_rect' in element:
            iframe_rect = element['iframe_rect']
            print(f"    iframe位置: x={iframe_rect['x']:.0f}, y={iframe_rect['y']:.0f}, "
                  f"宽={iframe_rect['width']:.0f}, 高={iframe_rect['height']:.0f}")
    
    # 自动操作模式
    if auto_click and click_index is not None:
        element_index = click_index - 1
        if 0 <= element_index < len(elements):
            element = elements[element_index]
            operation_type = operation_type or "1"
            wait_for_navigation = wait_for_navigation if wait_for_navigation is not None else True
            
            print(f"\n自动操作模式: 对元素 {click_index} 执行操作...")
            return _perform_element_operation(browser_tool, page_index, element, operation_type, wait_for_navigation)
    
    # 交互式操作（只有在非自动模式且参数未提供时才进行）
    if not auto_click and (click_index is None and operation_type is None):
        print("\n您可以使用元素序号来执行后续操作，例如点击元素")
        print("提示：在非交互模式下，请使用auto_click=True和click_index参数来自动操作元素")
            
    # 返回查找结果，以便其他函数使用
    return result


def _perform_element_operation(browser_tool, page_index, element, operation_type, wait_for_navigation):
    """执行元素操作的辅助函数"""
    # 判断是否来自iframe
    from_iframe = element.get('from_iframe', False)
    
    # 获取选择器
    selector = element.get('cssSelector')
    if not selector:
        print("该元素没有有效的CSS选择器")
        return
    
    # 进行操作
    if operation_type == "1":
        # 点击元素
        print(f"\n正在点击元素...")
        
        # 对于iframe内的元素，我们需要特殊处理
        if from_iframe:
            iframe_index = element.get('iframe_index', 0)
            print(f"注意: 元素位于iframe中 (索引: {iframe_index})，将使用直接方法点击")
            
            # 使用专门的iframe点击函数
            direct_click_result = direct_click_in_iframe(
                browser_tool=browser_tool,
                page_index=page_index,
                iframe_index=iframe_index,
                selector=selector,
                wait_for_navigation=wait_for_navigation
            )
            
            if direct_click_result['success']:
                print(f"在iframe中点击成功!")
                return direct_click_result
                
            print("直接点击方法失败，尝试常规点击...")
        
        # 常规点击（如果不在iframe中或iframe直接点击失败）
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
            
            # 如果点击失败且元素来自iframe，提供更多信息
            if from_iframe:
                print("\n对于iframe内的元素，您可能需要:")
                print("1. 先切换到iframe内部")
                print("2. 在iframe上下文中执行点击")
                print("3. 或者使用JavaScript在iframe内执行点击")
                
        return click_result
        
    elif operation_type == "2":
        # 双击
        print(f"\n正在双击元素...")
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
        
        return click_result
            
    elif operation_type == "3":
        # 悬停
        print(f"\n正在悬停在元素上...")
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
        
        return hover_result
            
    elif operation_type == "4":
        # 高亮显示
        print(f"\n正在高亮显示元素...")
        print("高亮显示功能暂未实现")
        return {"success": False, "message": "高亮显示功能暂未实现"}
        
    else:
        print("无效的操作类型")
        return {"success": False, "message": "无效的操作类型"}