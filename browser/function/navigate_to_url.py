import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))



def navigate_to_url(browser_tool, page_index=None, url=None):
    """导航到指定URL
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要导航的页面序号，默认0
        url: 要导航到的URL，默认为空
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取页面序号，如果没有提供则使用默认值
    if page_index is None:
        page_index = 0  # 默认使用第一个页面
    
    # 获取URL，如果没有提供则返回错误
    if url is None:
        print("错误: 必须提供url参数")
        return
    
    print(f"\n正在导航页面 {page_index} 到: {url}")
    
    result = browser_tool.navigate_to_url(page_index, url)
    
    if result['success']:
        print(f"导航成功!")
        print(f"页面标题: {result['title']}")
        print(f"当前URL: {result['url']}")
    else:
        print(f"导航失败: {result['message']}")
    
    return result
