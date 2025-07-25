import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))




def switch_page(browser_tool, page_index=None):
    """切换到指定页面
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要切换到的页面序号，默认为None（需要输入或使用默认值0）
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取当前页面列表
    pages_result = browser_tool.get_pages()
    if not pages_result['success']:
        print(f"获取页面列表失败: {pages_result['message']}")
        return
    
    pages = pages_result['pages']
    if not pages:
        print("没有可用的页面")
        return
    
    # 显示当前页面列表
    print(f"\n当前有 {len(pages)} 个页面:")
    for i, page in enumerate(pages):
        print(f"[{i}] {page.get('title', '无标题')} - {page.get('url', '无URL')}")
    
    # 获取要切换的页面序号
    if page_index is None:
        print("错误: 必须提供page_index参数")
        return
    
    # 验证页面序号有效性
    if page_index < 0 or page_index >= len(pages):
        print(f"页面序号无效，必须在0到{len(pages)-1}之间")
        return
    
    print(f"\n正在切换到页面 {page_index}...")
    
    result = browser_tool.switch_page(page_index)
    
    if result['success']:
        print(f"切换成功!")
        print(f"页面标题: {result['title']}")
        print(f"页面URL: {result['url']}")
    else:
        print(f"切换失败: {result['message']}")
    
    return result