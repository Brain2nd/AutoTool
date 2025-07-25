import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# 导入依赖函数
from .direct_click_in_iframe import direct_click_in_iframe

def get_clickable_elements(browser_tool, page_index=None, include_iframes=None,
                          show_details=None, auto_click=False, element_index=None,
                          operation_type='click', wait_for_navigation=True):
    """获取指定页面所有可点击的元素
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要获取可点击元素的页面序号
        include_iframes: 是否在iframe中查找元素，默认True
        show_details: 是否显示详细信息 (True/False)
        auto_click: 是否自动点击某个元素
        element_index: 要点击的元素序号 (1-based)
        operation_type: 操作类型 ('click', 'dblclick', 'hover', 'highlight')
        wait_for_navigation: 是否等待页面导航
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取要查询的页面序号
    if page_index is None:
        page_index = 0  # 默认使用第一个页面
        
    # 是否包含iframe中的元素
    if include_iframes is None:
        include_iframes = True  # 默认包含iframe
    
    print(f"\n正在获取页面 {page_index} 的可点击元素...")
    print(f"包含iframe: {'是' if include_iframes else '否'}")
    
    result = browser_tool.get_clickable_elements(page_index, include_iframes)
    
    if not result['success']:
        print(f"获取元素失败: {result['message']}")
        return
    
    # 显示结果
    print(f"获取可点击元素成功!")
    print(f"页面标题: {result['title']}")
    print(f"页面URL: {result['url']}")
    
    # 获取元素列表
    elements = result['elements']
    
    if not elements:
        print("未找到可点击元素")
        return
    
    # 分类元素
    iframe_elements = [e for e in elements if e.get('from_iframe', False)]
    main_elements = [e for e in elements if not e.get('from_iframe', False)]
    
    print(f"\n找到 {len(elements)} 个可点击元素:")
    print(f"- 主页面: {len(main_elements)} 个元素")
    print(f"- iframe内: {len(iframe_elements)} 个元素")
    
    # 分类统计
    element_types = {}
    iframe_stats = {}
    
    for element in elements:
        element_type = element.get('type', 'unknown')
        element_types[element_type] = element_types.get(element_type, 0) + 1
        
        # 如果是iframe元素，统计iframe信息
        if element.get('from_iframe', False):
            iframe_name = element.get('iframe_name', 'unknown')
            iframe_stats[iframe_name] = iframe_stats.get(iframe_name, 0) + 1
    
    # 显示元素类型统计
    print("\n元素类型统计:")
    for element_type, count in element_types.items():
        print(f"- {element_type}: {count} 个")
    
    # 显示iframe统计
    if iframe_elements:
        print("\niframe元素统计:")
        for iframe_name, count in iframe_stats.items():
            print(f"- {iframe_name}: {count} 个元素")
    
    # 询问是否显示详细信息（只在交互模式下询问）
    if show_details is None:
        show_details = False  # 默认不显示详细信息
    
    if show_details:
        print("\n所有可点击元素:")
        for i, element in enumerate(elements):
            # 元素基本信息
            element_type = element.get('type', 'unknown')
            element_text = element.get('text', '')
            element_tag = element.get('tagName', 'unknown')
            
            # 判断是否来自iframe
            from_iframe = element.get('from_iframe', False)
            iframe_info = ""
            
            if from_iframe:
                iframe_name = element.get('iframe_name', 'unknown')
                iframe_info = f" [来自iframe: {iframe_name}]"
            
            # 元素位置
            rect = element.get('rect', {})
            position_info = f"位置: x={rect.get('x', 0):.0f}, y={rect.get('y', 0):.0f}"
            
            # 截断过长的文本
            if len(element_text) > 40:
                element_text = element_text[:37] + "..."
                
            print(f"[{i+1}] {element_type} <{element_tag}>: '{element_text}'{iframe_info}")
            print(f"    {position_info}, 宽={rect.get('width', 0):.0f}, 高={rect.get('height', 0):.0f}")
            
            # 显示选择器
            if 'cssSelector' in element:
                selector = element['cssSelector']
                if len(selector) > 60:
                    selector = selector[:57] + "..."
                print(f"    选择器: {selector}")
            
            # 如果是链接，显示链接地址
            if element_type == 'link' and 'href' in element:
                href = element['href']
                if href and len(href) > 60:
                    href = href[:57] + "..."
                print(f"    链接: {href}")
    else:
        # 只显示部分元素
        max_display = min(10, len(elements))
        print(f"\n显示前 {max_display} 个元素:")
        
        for i in range(max_display):
            element = elements[i]
            element_type = element.get('type', 'unknown')
            element_text = element.get('text', '')
            
            # 判断是否来自iframe
            from_iframe = element.get('from_iframe', False)
            iframe_info = ""
            
            if from_iframe:
                iframe_name = element.get('iframe_name', 'unknown')
                iframe_info = f" [来自iframe: {iframe_name}]"
                
            # 截断过长的文本
            if len(element_text) > 40:
                element_text = element_text[:37] + "..."
                
            print(f"[{i+1}] {element_type}: '{element_text}'{iframe_info}")
    
    # 自动操作模式
    if auto_click and element_index is not None:
        element_idx = element_index - 1
        if 0 <= element_idx < len(elements):
            element = elements[element_idx]
            print(f"\n自动操作模式: 对元素 {element_index} 执行 {operation_type} 操作...")
            return _perform_element_operation(browser_tool, page_index, element, operation_type, wait_for_navigation)
        else:
            print(f"无效的元素序号: {element_index}，有效范围: 1-{len(elements)}")
            return
    
    # 如果是非自动模式，只显示提示信息
    if not auto_click:
        print("\n提示：使用auto_click=True和element_index参数来自动操作元素")
        return {
            "success": True,
            "message": "可点击元素获取完成，使用auto_click=True来进行操作",
            "elements": elements,
            "total_elements": len(elements)
        }
            
    # 提供返回结果的选项
    return result


def _perform_element_operation(browser_tool, page_index, element, operation_type, wait_for_navigation):
    """执行元素操作的辅助函数"""
    # 判断是否来自iframe
    from_iframe = element.get('from_iframe', False)
    
    # 获取选择器
    selector = element.get('cssSelector')
    if not selector:
        print("该元素没有有效的CSS选择器")
        return {"success": False, "message": "该元素没有有效的CSS选择器"}
    
    # 进行操作
    if operation_type == "click":
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
        
    elif operation_type == "dblclick":
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
        
    elif operation_type == "hover":
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
        
    elif operation_type == "highlight":
        # 高亮显示
        print(f"\n正在高亮显示元素...")
        print("高亮显示功能暂未实现")
        return {"success": False, "message": "高亮显示功能暂未实现"}
        
    else:
        print(f"无效的操作类型: {operation_type}")
        return {"success": False, "message": f"无效的操作类型: {operation_type}"}