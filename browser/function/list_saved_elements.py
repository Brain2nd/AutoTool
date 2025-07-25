import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))


def list_saved_elements(browser_tool, directory=None):
    """列出已保存的元素
    
    Args:
        browser_tool: 浏览器工具实例
        directory: 要查看的目录路径，如果为None则查看默认缓存目录
    """
    if not browser_tool:
        print("错误: 浏览器工具未初始化")
        return
    
    # 使用默认目录或指定目录
    if directory is None:
        directory = None  # 使用默认缓存目录
    
    print(f"\n正在获取{'指定目录' if directory else '默认缓存目录'}中的保存元素...")
    result = browser_tool.list_saved_elements(directory)
    
    if not result['success']:
        print(f"获取保存元素失败: {result['message']}")
        return
    
    # 显示结果
    print(f"获取保存元素成功!")
    print(f"找到 {len(result['elements'])} 个已保存的元素")
    
    if result['elements']:
        print("\n已保存的元素列表:")
        for i, element in enumerate(result['elements']):
            print(f"[{i+1}] {element['name']}: 类型:{element['type']}, 文本:'{element['text']}'")
            print(f"    文件路径: {element['file_path']}")
            print(f"    选择器: {element['selector']}")
    else:
        print("没有找到任何已保存的元素")
    
    return result