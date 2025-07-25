import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))



def extract_tag_from_selector(selector):
    """从选择器中提取标签类型"""
    # 常见的交互元素
    common_tags = ['button', 'a', 'input']
    
    for tag in common_tags:
        if tag in selector:
            return tag
    
    # 如果选择器中没有已知标签，尝试提取第一个标签
    import re
    match = re.search(r'^([a-zA-Z]+)', selector)
    if match:
        return match.group(1)
    
    return None