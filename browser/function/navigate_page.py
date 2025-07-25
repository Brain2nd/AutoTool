import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))


def navigate_page(browser_tool, page_index=None, url=None):
    """让指定序号的页面导航到URL
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要导航的页面序号
        url: 要导航到的URL
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取要导航的页面序号
    if page_index is None:
        print("错误: 必须指定要导航的页面序号")
        return
    
    # 获取要导航的URL
    if url is None:
        print("错误: 必须指定要导航到的URL")
        return
    
    # 确保URL包含协议
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    print(f"\n正在将页面 {page_index} 导航到 {url}...")
    result = browser_tool.navigate_page(page_index, url)
    
    if not result['success']:
        print(f"导航失败: {result['message']}")
        return
    
    print(f"导航成功!")
    print(f"页面 {page_index} 的新标题: {result['title']}")
    print(f"页面的新URL: {result['url']}")
    print(f"状态码: {result['status']}")
    
    return result