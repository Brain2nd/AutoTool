import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

def load_elements(browser_tool, element_identifier=None, load_type=None, 
                 operate_on_element=None, element_index=None, page_index=None,
                 operation_type='click', text_input=None, wait_for_navigation=True):
    """加载保存的元素
    
    Args:
        browser_tool: 浏览器工具实例
        element_identifier: 元素标识符（名称、路径、名称列表等）
        load_type: 加载类型 (1=单个元素名称, 2=多个元素名称, 3=目录, 4=文件路径)
        operate_on_element: 是否对加载的元素进行操作 (True/False)
        element_index: 要操作的元素序号 (1-based)
        page_index: 要操作元素的页面序号
        operation_type: 操作类型 ('click', 'dblclick', 'hover', 'input', 'attributes')
        text_input: 要输入的文本 (当operation_type为'input'时)
        wait_for_navigation: 是否等待页面导航
    """
    if not browser_tool:
        print("错误: 浏览器工具未初始化")
        return
    
    # 如果没有提供参数，则使用默认值或返回错误
    if element_identifier is None or load_type is None:
        print("错误: 必须提供element_identifier和load_type参数")
        return
    
    print(f"\n正在加载元素...")
    result = browser_tool.load_elements(element_identifier)
    
    if not result['success']:
        print(f"加载元素失败: {result['message']}")
        return
    
    # 显示结果
    print(f"加载元素成功!")
    print(f"共加载了 {len(result['elements'])} 个元素")
    
    if result['elements']:
        print("\n已加载的元素列表:")
        for i, element in enumerate(result['elements']):
            element_name = result['element_names'][i] if i < len(result['element_names']) else f"元素{i+1}"
            print(f"[{i+1}] {element_name}: 类型:{element.get('type', '未知')}, 文本:'{element.get('text', '')}'")
            print(f"    选择器: {element.get('cssSelector', '')}")
            
        # 询问是否要对加载的元素进行操作
        if browser_tool.is_connected():
            # 如果没有提供operate_on_element参数，则使用默认值
            if operate_on_element is None:
                operate_on_element = False  # 默认不进行操作
            
            if operate_on_element:
                try:
                    # 如果没有提供element_index，则返回错误
                    if element_index is None:
                        print("错误: 必须提供element_index参数")
                        return
                    
                    # 转换为0-based索引
                    element_idx = element_index - 1 if isinstance(element_index, int) else element_index
                    
                    if element_idx < 0 or element_idx >= len(result['elements']):
                        print(f"无效的序号，有效范围: 1-{len(result['elements'])}")
                        return
                    
                    element = result['elements'][element_idx]
                    element_name = result['element_names'][element_idx] if element_idx < len(result['element_names']) else f"元素{element_idx+1}"
                    selector = element.get('cssSelector')
                    
                    if not selector:
                        print(f"元素 '{element_name}' 没有有效的选择器")
                        return
                    
                    # 获取页面序号
                    if page_index is None:
                        page_index = 0  # 默认使用第一个页面
                    
                    # 使用提供的operation_type参数，不再进行交互式询问
                    
                    # 根据操作类型执行不同操作
                    if operation_type == 'click':
                        # 使用提供的wait_for_navigation参数，不再进行交互式询问
                        
                        print(f"\n正在页面 {page_index} 中点击元素 '{element_name}'...")
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
                            
                    elif operation_type == 'dblclick':
                        # 双击
                        print(f"\n正在页面 {page_index} 中双击元素 '{element_name}'...")
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
                            
                    elif operation_type == 'hover':
                        # 悬停
                        print(f"\n正在页面 {page_index} 中悬停在元素 '{element_name}' 上...")
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
                            
                    elif operation_type == 'input':
                        # 输入文本
                        if text_input is None:
                            print("错误: 必须提供text_input参数")
                            return
                        
                        print(f"\n正在向元素 '{element_name}' 输入文本...")
                        
                        # 这需要额外的浏览器功能，目前示例中未实现
                        print("输入文本功能暂未实现，请在BrowserTool中添加此功能")
                        
                    elif operation_type == 'attributes':
                        # 获取元素属性
                        print(f"\n元素 '{element_name}' 的属性:")
                        for key, value in element.items():
                            if key != 'attributes' and key != 'rect':
                                print(f"  {key}: {value}")
                        
                        # 显示详细属性
                        if element.get('attributes'):
                            print("\n详细HTML属性:")
                            for attr_name, attr_value in element['attributes'].items():
                                print(f"  {attr_name}: {attr_value}")
                    else:
                        print(f"无效的操作类型: {operation_type}")
                        
                except ValueError:
                    print("输入错误，必须是整数")
                    return
    
    return result