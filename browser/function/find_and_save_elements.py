import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))


def find_and_save_elements(browser_tool, page_index=None, description=None, 
                          similarity_threshold=None, save_path=None, prefix=None,
                          max_results=None, include_iframes=None):
    """查找并保存元素到本地
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要查找并保存元素的页面序号
        description: 功能描述(例如: '登录', '搜索', '下一页')
        similarity_threshold: 相似度阈值，默认0.3
        save_path: 保存路径，默认保存到元素缓存目录
        prefix: 文件名前缀，默认为空
        max_results: 最大保存数量，默认5
        include_iframes: 是否在iframe中查找元素，默认True
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取要查询的页面序号
    if page_index is None:
        print("错误: 必须指定要查找并保存元素的页面序号")
        return
    
    # 获取功能描述
    if description is None:
        print("错误: 必须指定功能描述(例如: '登录', '搜索', '下一页')")
        return
    
    # 设置相似度阈值
    if similarity_threshold is None:
        similarity_threshold = 0.3
    
    # 设置保存路径
    if save_path is None:
        save_path = None  # 使用默认路径
    
    # 设置前缀
    if prefix is None:
        prefix = ""
                
    # 设置最大保存数量
    if max_results is None:
        max_results = 5
                
    # 设置是否在iframe中查找元素
    if include_iframes is None:
        include_iframes = True
    
    print(f"\n正在页面 {page_index} 中查找与 '{description}' 相匹配的元素并保存 (阈值: {similarity_threshold})...")
    print(f"包含iframe: {'是' if include_iframes else '否'}")
    
    result = browser_tool.find_and_save_elements(
        page_index=page_index,
        description=description,
        similarity_threshold=similarity_threshold,
        save_path=save_path,
        prefix=prefix,
        max_results=max_results,
        include_iframes=include_iframes
    )
    
    if not result['success']:
        print(f"查找并保存元素失败: {result['message']}")
        return
    
    # 显示结果
    print(f"查找并保存元素成功!")
    print(f"{result['message']}")
    
    # 显示保存路径信息
    save_path_info = result.get('save_path', '默认路径')
    print(f"\n保存位置: {save_path_info}")
    
    # 显示保存的文件和元素名称
    print("\n已保存的元素文件:")
    for i, file_path in enumerate(result['saved_elements']):
        element_name = result['element_names'][i]
        print(f"[{i+1}] {element_name}: {file_path}")
    
    # 显示匹配元素详情
    if result['matches']:
        print("\n匹配元素详情(按相似度排序):")
        for i, element in enumerate(result['matches']):
            if i >= len(result['element_names']):
                break
                
            element_name = result['element_names'][i]
            
            # 判断元素是否来自iframe
            from_iframe = element.get('from_iframe', False)
            iframe_info = ""
            
            if from_iframe:
                iframe_name = element.get('iframe_name', 'unknown')
                iframe_info = f" [来自iframe: {iframe_name}]"
            
            # 获取相似度
            similarity = element.get('similarity', 0)
            
            print(f"[{i+1}] {element_name}: 相似度: {similarity:.2f}, {element.get('type', 'unknown')}: '{element.get('text', '')}'")
            print(f"    {iframe_info}")
            
            # 显示选择器
            selector = element.get('cssSelector', '')
            if len(selector) > 60:
                selector = selector[:57] + "..."
            print(f"    选择器: {selector}")
            
            # 显示元素位置
            if 'rect' in element:
                rect = element['rect']
                x = rect.get('x', 0)
                y = rect.get('y', 0)
                width = rect.get('width', 0)
                height = rect.get('height', 0)
                print(f"    位置: x={x:.0f}, y={y:.0f}, 宽={width:.0f}, 高={height:.0f}")
            
            # 如果是iframe内的元素，显示iframe位置
            if from_iframe and 'iframe_rect' in element:
                iframe_rect = element['iframe_rect']
                print(f"    iframe位置: x={iframe_rect['x']:.0f}, y={iframe_rect['y']:.0f}, "
                      f"宽={iframe_rect['width']:.0f}, 高={iframe_rect['height']:.0f}")
    
    # 提示用户如何使用保存的元素
    if result['element_names'] and result['saved_elements']:
        print("\n您可以使用以下方式点击这些保存的元素:")
        print("1. 使用\"点击已保存的元素\"功能并选择对应元素")
        if len(result['element_names']) > 0:
            element_name = result['element_names'][0]
            print(f"2. 使用代码: browser_tool.click_saved_element(\"{element_name}\", page_index)")
        if len(result['saved_elements']) > 0:
            element_path = result['saved_elements'][0]
            print(f"3. 使用文件路径: browser_tool.click_saved_element(\"{element_path}\", page_index)")
    
    return result
