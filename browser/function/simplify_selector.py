import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))


def simplify_selector(selector):
    """简化复杂的CSS选择器"""
    parts = selector.split('>')
    if len(parts) <= 1:
        return selector
        
    # 取最后一部分，通常是目标元素
    last_part = parts[-1].strip()
    
    # 提取最重要的选择器部分（通常是按钮、链接或具有类的元素）
    if 'button' in last_part or 'a' in last_part or '.btn' in last_part:
        return last_part
    
    # 如果有ID选择器，优先使用
    for part in reversed(parts):
        if '#' in part:
            return part.strip()
    
    # 如果有特定的类，使用特定类
    for part in reversed(parts):
        if '.btn' in part or '.button' in part:
            return part.strip()
    
    # 默认返回最后一部分
    return last_part