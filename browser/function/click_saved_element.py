import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

def click_saved_element(browser_tool, element_name=None, page_index=None, 
                       click_type='click', wait_for_navigation=True):
    """点击已保存的元素
    
    Args:
        browser_tool: 浏览器工具实例
        element_name: 要点击的元素名称或路径
        page_index: 要操作的页面序号
        click_type: 点击类型 ('click', 'dblclick', 'hover')
        wait_for_navigation: 是否等待页面导航
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 如果没有提供元素名称，返回错误
    if element_name is None:
        print("错误: 必须提供element_name参数")
        return
    
    # 获取页面序号
    if page_index is None:
        page_index = 0  # 默认使用第一个页面
    
    # 使用提供的参数，不再进行交互式询问
    
    print(f"\n正在页面 {page_index} 中点击已保存的元素 '{element_name}'...")
    result = browser_tool.click_saved_element(
        element_name=element_name,
        page_index=page_index,
        click_type=click_type,
        wait_for_navigation=wait_for_navigation
    )
    
    if not result['success']:
        print(f"点击已保存元素失败: {result['message']}")
        # 提供进一步的诊断信息
        print("\n正在尝试其他加载方式...")
        
        # 尝试直接从文件加载
        if element_name and element_name != "内存缓存":
            print(f"尝试直接从文件加载: {element_name}")
            load_result = browser_tool.load_elements(element_name)
            if load_result['success'] and load_result['elements']:
                element = load_result['elements'][0]
                selector = element.get('cssSelector')
                if selector:
                    print(f"找到选择器: {selector}")
                    print("尝试直接点击...")
                    click_result = browser_tool.click_element(
                        page_index=page_index,
                        element_selector=selector,
                        click_type=click_type,
                        wait_for_navigation=wait_for_navigation
                    )
                    if click_result['success']:
                        print(f"直接点击成功!")
                        print(f"页面标题: {click_result['title']}")
                        print(f"页面URL: {click_result['url']}")
                        return click_result
        
        print("所有尝试均失败")
        return
    
    # 显示结果
    print(f"点击已保存元素成功!")
    print(f"页面标题: {result['title']}")
    print(f"页面URL: {result['url']}")
    
    return result