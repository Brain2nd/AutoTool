import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))



def wait_and_get_page_info(browser_tool, page_index, wait_for_navigation, result):
    """等待导航并获取页面信息"""
    try:
        # 等待可能的导航
        if wait_for_navigation:
            print("等待页面可能的导航...")
            try:
                # 不使用字符串作为参数，避免不可调用错误
                browser_tool._async_loop.run_until_complete(
                    browser_tool.context.pages[page_index].wait_for_navigation(timeout=5000)
                )
            except Exception as nav_error:
                # 这个错误可以忽略，有些点击操作不会触发导航
                pass
        
        # 获取当前页面信息 - 可能失败，但不影响结果
        try:
            result['title'] = browser_tool._async_loop.run_until_complete(
                browser_tool.context.pages[page_index].title()
            )
            result['url'] = browser_tool._async_loop.run_until_complete(
                browser_tool.context.pages[page_index].url()
            )
        except:
            # 忽略错误，不显示任何错误信息
            result['title'] = ""
            result['url'] = ""
    except Exception:
        # 完全忽略所有错误
        pass