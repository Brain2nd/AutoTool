import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))



def create_new_tab(browser_tool, url=None):
    """创建新的标签页
    
    Args:
        browser_tool: 浏览器工具实例
        url: 要导航到的URL，如果为None则询问用户或创建空白页
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 如果URL为None，则创建空白标签页
    if url is None:
        url = 'about:blank'  # 使用空白页
    
    print(f"\n正在创建新标签页 {'[空白页]' if url == 'about:blank' else url}...")
    result = browser_tool.create_new_tab(url)
    
    if not result['success']:
        print(f"创建失败: {result['message']}")
        return
    
    print(f"创建成功!")
    print(f"页面序号: {result['page_index']}")
    print(f"页面标题: {result['title']}")
    print(f"当前URL: {result['url']}")
    
    return result
