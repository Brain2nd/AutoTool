import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))



def navigate(browser_tool, url=None):
    """导航到指定URL
    
    Args:
        browser_tool: 浏览器工具实例
        url: 要导航到的URL，如果为None则提示用户输入
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 如果没有指定URL，提示用户输入
    if url is None:
        print("错误: 必须指定要导航到的URL")
        return
    
    # 确保URL包含协议
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    print(f"\n正在导航到 {url}...")
    result = browser_tool.navigate(url)
    
    if not result['success']:
        print(f"导航失败: {result['message']}")
        return
    
    print(f"导航成功!")
    print(f"页面标题: {result['title']}")
    print(f"当前URL: {result['url']}")
    print(f"状态码: {result['status']}")
    
    return result

