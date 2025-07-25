import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))


def get_pages(browser_tool):
    """演示如何获取页面列表"""
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取连接信息
    info = browser_tool.get_connection_info()
    
    print("\n浏览器连接信息:")
    for key, value in info.items():
        print(f"{key}: {value}")
    
    # 获取页面列表
    print("\n获取页面列表...")
    
    # 由于无法直接获取页面列表，我们通过重新连接的方式获取
    result = browser_tool.connect_to_browser(
        browser_type=info.get('browser_type', 'chromium'),
        endpoint_url=info.get('endpoint_url')  # 直接使用已连接的endpoint_url，让系统自动检测
    )
    
    if result['success'] and 'pages' in result:
        print("\n可用页面列表:")
        for page in result['pages']:
            print(f"[{page['index']}] {page['title']} - {page['url']}")
    else:
        print("获取页面列表失败")