import pathlib
import sys


current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))


# 导入依赖的函数
from .direct_click_in_iframe import direct_click_in_iframe


def find_and_click_list_items(browser_tool, page_index=None, include_iframes=None,
                             list_index=None, display_mode='1', auto_click=False,
                             item_index=None, clickable_index=None, wait_for_navigation=True):
    """查找列表并尝试点击指定列表项
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要查找列表的页面序号，默认0
        include_iframes: 是否在iframe中查找，默认True
        list_index: 要选择的列表序号 (1-based)，如果为None则仅显示列表信息
        display_mode: 显示模式 ('1'=简洁, '2'=标准, '3'=详细, '4'=层次结构)，默认'1'
        auto_click: 是否自动点击列表项，默认False
        item_index: 要点击的列表项序号 (1-based)，如果auto_click为True时使用
        clickable_index: 可点击元素序号 (1-based)，用于指定点击哪个可点击元素
        wait_for_navigation: 是否等待页面导航，默认True
    """
    if not browser_tool or not browser_tool.is_connected():
        print("错误: 浏览器未连接")
        return
    
    # 获取要查询的页面序号
    if page_index is None:
        page_index = 0  # 默认使用第一个页面
    
    # 是否在iframe中查找
    if include_iframes is None:
        include_iframes = True  # 默认包含iframe
    
    print(f"\n正在自动查找页面 {page_index} 中的所有列表...")
    
    # 查找页面中的所有列表的JavaScript
    find_all_lists_js = """
    () => {
        // 首先定义getCssSelector函数，确保在使用前已定义
        function getCssSelector(element) {
            if (!element) return '';
            
            let path = [];
            while (element.nodeType === Node.ELEMENT_NODE) {
                let selector = element.nodeName.toLowerCase();
                
                if (element.id) {
                    selector += '#' + element.id;
                    path.unshift(selector);
                    break;
                } else if (element.className) {
                    // 确保className是字符串类型，处理SVG元素等特殊情况
                    let classValue = '';
                    if (typeof element.className === 'string') {
                        classValue = element.className;
                    } else if (element.className.baseVal !== undefined) {
                        // SVG元素的className是一个SVGAnimatedString对象
                        classValue = element.className.baseVal;
                    }
                    
                    const classes = classValue.split(/\\s+/).filter(Boolean);
                    if (classes.length > 0) {
                        selector += '.' + classes.join('.');
                    }
                }
                
                let sibling = element;
                let index = 1;
                while (sibling = sibling.previousElementSibling) {
                    if (sibling.nodeName.toLowerCase() === selector.split('.')[0]) {
                        index++;
                    }
                }
                
                if (index > 1) {
                    selector += ':nth-of-type(' + index + ')';
                }
                
                path.unshift(selector);
                element = element.parentNode;
                
                // 限制选择器长度
                if (path.length >= 3) {
                    break;
                }
            }
            
            return path.join(' > ');
        }
        
        // 只查找标准HTML列表
        const standardLists = [];
        
        // 查找所有ul、ol、dl元素（标准列表元素）
        const ulElements = document.querySelectorAll('ul');
        const olElements = document.querySelectorAll('ol');
        const dlElements = document.querySelectorAll('dl');
        
        console.log(`找到 ${ulElements.length} 个 ul 元素`);
        console.log(`找到 ${olElements.length} 个 ol 元素`);
        console.log(`找到 ${dlElements.length} 个 dl 元素`);
        
        // 处理所有ul元素
        ulElements.forEach(ul => {
            // 验证是否有li子元素
            const liElements = ul.querySelectorAll('li');
            if (liElements.length > 0) {
                // 收集子元素信息
                const childrenInfo = Array.from(liElements).slice(0, 10).map(li => {
                    return {
                        tagName: 'li',
                        className: li.className || '',
                        text: (li.innerText || li.textContent || '').substring(0, 100)
                    };
                });
                
                standardLists.push({
                    selector: getCssSelector(ul),
                    tagName: 'ul',
                    id: ul.id || '',
                    className: ul.className || '',
                    childCount: liElements.length,
                    listItemTag: 'li',
                    preview: childrenInfo,
                    isStandardList: true,
                    position: ul.getBoundingClientRect()
                });
            }
        });
        
        // 处理所有ol元素
        olElements.forEach(ol => {
            const liElements = ol.querySelectorAll('li');
            if (liElements.length > 0) {
                const childrenInfo = Array.from(liElements).slice(0, 10).map(li => {
                    return {
                        tagName: 'li',
                        className: li.className || '',
                        text: (li.innerText || li.textContent || '').substring(0, 100)
                    };
                });
                
                standardLists.push({
                    selector: getCssSelector(ol),
                    tagName: 'ol',
                    id: ol.id || '',
                    className: ol.className || '',
                    childCount: liElements.length,
                    listItemTag: 'li',
                    preview: childrenInfo,
                    isStandardList: true,
                    position: ol.getBoundingClientRect()
                });
            }
        });
        
        // 处理所有dl元素
        dlElements.forEach(dl => {
            const dtElements = dl.querySelectorAll('dt');
            const ddElements = dl.querySelectorAll('dd');
            if (dtElements.length > 0 || ddElements.length > 0) {
                // 收集dt和dd元素信息
                const childrenInfo = [];
                dtElements.forEach(dt => {
                    childrenInfo.push({
                        tagName: 'dt',
                        className: dt.className || '',
                        text: (dt.innerText || dt.textContent || '').substring(0, 100)
                    });
                });
                
                ddElements.forEach(dd => {
                    childrenInfo.push({
                        tagName: 'dd',
                        className: dd.className || '',
                        text: (dd.innerText || dd.textContent || '').substring(0, 100)
                    });
                });
                
                standardLists.push({
                    selector: getCssSelector(dl),
                    tagName: 'dl',
                    id: dl.id || '',
                    className: dl.className || '',
                    childCount: dtElements.length + ddElements.length,
                    listItemTag: 'dt/dd',
                    preview: childrenInfo.slice(0, 10),
                    isStandardList: true,
                    position: dl.getBoundingClientRect()
                });
            }
        });
        
        // 检查是否有嵌套列表，同时只保留有效的列表
        const finalLists = [];
        const processedElements = new Set();
        
        // 首先处理所有列表
        for (const list of standardLists) {
            // 找到DOM元素
            let element;
            if (list.tagName === 'ul') {
                element = document.querySelector(list.selector);
            } else if (list.tagName === 'ol') {
                element = document.querySelector(list.selector);
            } else if (list.tagName === 'dl') {
                element = document.querySelector(list.selector);
            }
            
            if (!element || processedElements.has(element)) {
                continue;
            }
            
            // 检查是否是顶级列表或是被识别的列表中的子列表
            let isNestedList = false;
            for (const otherList of standardLists) {
                if (list === otherList) continue;
                
                const otherElement = document.querySelector(otherList.selector);
                if (otherElement && otherElement.contains(element)) {
                    isNestedList = true;
                    break;
                }
            }
            
            // 如果不是嵌套列表，则添加到最终列表
            if (!isNestedList) {
                finalLists.push(list);
                processedElements.add(element);
                
                // 查找嵌套列表
                const nestedLists = [];
                const childLists = element.querySelectorAll('ul, ol, dl');
                for (const childList of childLists) {
                    if (processedElements.has(childList)) continue;
                    
                    processedElements.add(childList);
                    const childTagName = childList.tagName.toLowerCase();
                    
                    let childItemCount = 0;
                    let childItemTag = '';
                    
                    if (childTagName === 'ul' || childTagName === 'ol') {
                        const childItems = childList.querySelectorAll('li');
                        childItemCount = childItems.length;
                        childItemTag = 'li';
                    } else if (childTagName === 'dl') {
                        const dtItems = childList.querySelectorAll('dt');
                        const ddItems = childList.querySelectorAll('dd');
                        childItemCount = dtItems.length + ddItems.length;
                        childItemTag = 'dt/dd';
                    }
                    
                    if (childItemCount > 0) {
                        nestedLists.push({
                            tagName: childTagName,
                            selector: getCssSelector(childList),
                            id: childList.id || '',
                            className: childList.className || '',
                            childCount: childItemCount,
                            isStandardList: true,
                            listItemTag: childItemTag
                        });
                    }
                }
                
                // 添加嵌套列表信息
                if (nestedLists.length > 0) {
                    list.hasNestedLists = true;
                    list.nestedListCount = nestedLists.length;
                    list.nestedLists = nestedLists;
                }
            }
        }
        
        // 排序：标准列表优先，然后是子元素多的列表
        finalLists.sort((a, b) => {
            // 按子元素数量排序
            return b.childCount - a.childCount;
        });
        
        return finalLists;
    }
    """
    
    try:
        # 先获取页面DOM
        dom_result = browser_tool.get_page_dom(page_index)
        if not dom_result['success']:
            print(f"获取DOM失败: {dom_result['message']}")
            return
        
        # 获取页面中的所有列表
        print("正在分析页面中的所有列表元素...")
        all_lists = browser_tool._async_loop.run_until_complete(
            browser_tool.context.pages[page_index].evaluate(find_all_lists_js)
        )
        
        main_page_lists = all_lists
        iframe_lists = []
        
        # 尝试在iframe中查找列表
        if include_iframes:
            print("正在查找iframe中的列表...")
            # 获取所有iframe
            iframe_handles = browser_tool._async_loop.run_until_complete(
                browser_tool.context.pages[page_index].query_selector_all('iframe')
            )
            
            if iframe_handles:
                print(f"发现 {len(iframe_handles)} 个iframe，正在检查...")
                
                # 遍历iframe查找列表
                for i, iframe_handle in enumerate(iframe_handles):
                    try:
                        # 获取iframe信息
                        iframe_id = browser_tool._async_loop.run_until_complete(iframe_handle.get_attribute('id')) or f"iframe_{i}"
                        iframe_name = browser_tool._async_loop.run_until_complete(iframe_handle.get_attribute('name')) or iframe_id
                        iframe_src = browser_tool._async_loop.run_until_complete(iframe_handle.get_attribute('src')) or ""
                        
                        # 获取iframe内容框架
                        content_frame = browser_tool._async_loop.run_until_complete(iframe_handle.content_frame())
                        if not content_frame:
                            continue
                        
                        # 在iframe中查找列表
                        iframe_lists_result = browser_tool._async_loop.run_until_complete(
                            content_frame.evaluate(find_all_lists_js)
                        )
                        
                        if iframe_lists_result and len(iframe_lists_result) > 0:
                            print(f"在iframe '{iframe_name}' 中找到 {len(iframe_lists_result)} 个列表！")
                            
                            # 将iframe信息添加到每个列表
                            for list_info in iframe_lists_result:
                                list_info['iframe'] = {
                                    'id': iframe_id,
                                    'name': iframe_name,
                                    'src': iframe_src,
                                    'index': i
                                }
                            
                            iframe_lists.extend(iframe_lists_result)
                        
                    except Exception as e:
                        print(f"处理iframe '{iframe_id}' 时出错: {str(e)}")
                    finally:
                        # 释放iframe句柄
                        browser_tool._async_loop.run_until_complete(iframe_handle.dispose())
        
        # 合并所有列表结果
        all_lists = main_page_lists + iframe_lists
        
        # 检查是否找到了列表
        if not all_lists or len(all_lists) == 0:
            print("未在页面或iframe中找到任何列表元素")
            return
        
        # 显示找到的列表
        print(f"\n共找到 {len(all_lists)} 个列表元素:")
        for i, list_info in enumerate(all_lists):
            # 显示列表基本信息
            list_tag = list_info['tagName']
            list_id = f"#{list_info['id']}" if list_info['id'] else ""
            list_class = f".{list_info['className'].replace(' ', '.')}" if list_info['className'] else ""
            list_selector = list_info['selector']
            child_count = list_info['childCount']
            
            # 检查是否在iframe中
            in_iframe = 'iframe' in list_info
            iframe_info = f" [来自iframe: {list_info['iframe']['name']}]" if in_iframe else ""
            
            # 检查是否是标准列表
            is_standard = list_info.get('isStandardList', False)
            list_item_tag = list_info.get('listItemTag', '')
            standard_marker = f" ★ 标准列表元素 <{list_tag}><{list_item_tag}>" if is_standard else ""
            
            # 为清晰显示，使用标号
            list_number = f"【列表{i+1}】"
            
            print(f"\n{list_number} {list_tag}{list_id}{list_class}{iframe_info}{standard_marker}")
            print(f"  子元素数量: {child_count}")
            print(f"  选择器: {list_selector}")
            
            # 显示前几个子元素的预览
            if 'preview' in list_info and list_info['preview']:
                print("  子元素预览:")
                for j, child in enumerate(list_info['preview']):
                    child_text = child['text'].replace('\n', ' ').strip()
                    child_tag = child.get('tagName', 'unknown')
                    if len(child_text) > 50:
                        child_text = child_text[:47] + "..."
                    # 使用子元素序号更清晰地标识
                    print(f"    • 子元素[{j+1}] {child_tag}: '{child_text}'")
            
            # 显示更多子元素数量信息
            if 'preview' in list_info and list_info['childCount'] > len(list_info['preview']):
                print(f"    • ... 还有 {list_info['childCount'] - len(list_info['preview'])} 个子元素未显示")
        
        # 检查是否提供了列表索引
        if list_index is None:
            print("请使用list_index参数指定要操作的列表序号 (1-based)")
            return {
                "success": True,
                "message": "找到列表，请指定list_index参数来操作特定列表",
                "lists": all_lists,
                "total_lists": len(all_lists)
            }
        
        # 验证列表索引
        selected_list_index = list_index - 1
        if selected_list_index < 0 or selected_list_index >= len(all_lists):
            print(f"无效的列表序号，有效范围: 1-{len(all_lists)}")
            return
            
        # 获取选中的列表信息
        selected_list = all_lists[selected_list_index]
        list_selector = selected_list['selector']
        in_iframe = 'iframe' in selected_list
        
        # 为选中的列表获取详细的列表项信息
        get_list_items_js = """
        (params) => {
            const listSelector = params.listSelector;
            
            // 查找列表元素
            const listElement = document.querySelector(listSelector);
            if (!listElement) {
                return { found: false, message: "未找到列表元素" };
            }
            
            // 获取CSS选择器函数定义
            function getCssSelector(element) {
                if (!element) return '';
                
                let path = [];
                while (element.nodeType === Node.ELEMENT_NODE) {
                    let selector = element.nodeName.toLowerCase();
                    
                    if (element.id) {
                        selector += '#' + element.id;
                        path.unshift(selector);
                        break;
                    } else if (element.className) {
                        // 确保className是字符串类型，处理SVG元素等特殊情况
                        let classValue = '';
                        if (typeof element.className === 'string') {
                            classValue = element.className;
                        } else if (element.className.baseVal !== undefined) {
                            // SVG元素的className是一个SVGAnimatedString对象
                            classValue = element.className.baseVal;
                        }
                        
                        const classes = classValue.split(/\\s+/).filter(Boolean);
                        if (classes.length > 0) {
                            selector += '.' + classes.join('.');
                        }
                    }
                    
                    let sibling = element;
                    let index = 1;
                    while (sibling = sibling.previousElementSibling) {
                        if (sibling.nodeName.toLowerCase() === selector.split('.')[0]) {
                            index++;
                        }
                    }
                    
                    if (index > 1) {
                        selector += ':nth-of-type(' + index + ')';
                    }
                    
                    path.unshift(selector);
                    element = element.parentNode;
                    
                    // 限制选择器长度
                    if (path.length >= 3) {
                        break;
                    }
                }
                
                return path.join(' > ');
            }
            
            // 查找可点击元素
            function findClickableElements(container) {
                const clickableElements = [];
                
                // 查找常见可点击元素
                const selectors = [
                    'a', 'button', 'input[type="button"]', 'input[type="submit"]',
                    '[role="button"]', '[role="link"]',
                    '.btn', '.button', '[class*="btn"]', '[class*="button"]',
                    '[onclick]', '[data-click]', '[data-action]'
                ];
                
                const potentialElements = container.querySelectorAll(selectors.join(','));
                potentialElements.forEach(el => {
                    // 过滤隐藏元素
                    const style = window.getComputedStyle(el);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {
                        clickableElements.push(el);
                    }
                });
                
                // 查找cursor:pointer的元素
                const allElements = container.querySelectorAll('*');
                allElements.forEach(el => {
                    if (clickableElements.includes(el)) return;
                    
                    const style = window.getComputedStyle(el);
                    if (style.cursor === 'pointer' && 
                        style.display !== 'none' && 
                        style.visibility !== 'hidden' && 
                        style.opacity !== '0') {
                        clickableElements.push(el);
                    }
                });
                
                return clickableElements;
            }

            // 获取列表项
            let listItems = [];
            const tagName = listElement.tagName.toLowerCase();
            
            // 针对标准列表结构(ul, ol, dl)的特殊处理
            if (tagName === 'ul' || tagName === 'ol') {
                // 对于ul和ol，只获取所有li子元素
                const liElements = listElement.querySelectorAll('li');
                if (liElements.length > 0) {
                    console.log(`找到标准列表，包含 ${liElements.length} 个li元素`);
                    listItems = Array.from(liElements);
                }
            } else if (tagName === 'dl') {
                // 对于dl，只获取dt和dd元素
                const dtElements = listElement.querySelectorAll('dt');
                const ddElements = listElement.querySelectorAll('dd');
                console.log(`找到dl列表，包含 ${dtElements.length} 个dt元素和 ${ddElements.length} 个dd元素`);
                listItems = Array.from([...dtElements, ...ddElements]);
            } else {
                // 不是标准列表，返回错误
                return { 
                    found: true, 
                    listElement: true,
                    message: "找到元素，但不是标准列表(ul/ol/dl)" 
                };
            }
            
            if (listItems.length === 0) {
                return { 
                    found: true, 
                    listElement: true,
                    message: "找到列表元素，但未找到列表项" 
                };
            }
            
            // 记录列表项识别结果
            console.log(`共找到 ${listItems.length} 个列表项`);
            
            // 获取元素属性
            function getElementAttributes(element) {
                const attributes = {};
                for (let i = 0; i < element.attributes.length; i++) {
                    const attr = element.attributes[i];
                    attributes[attr.name] = attr.value;
                }
                return attributes;
            }
            
            // 分析子元素结构
            function analyzeChildStructure(element, depth = 0, maxDepth = 2) {
                if (depth > maxDepth) {
                    return { type: 'max_depth_reached' };
                }
                
                const children = element.children;
                const result = [];
                
                for (let i = 0; i < children.length; i++) {
                    const child = children[i];
                    const tagName = child.tagName.toLowerCase();
                    const id = child.id ? '#' + child.id : '';
                    const className = child.className ? '.' + child.className.replace(/\\s+/g, '.') : '';
                    const text = (child.innerText || child.textContent || '').trim();
                    const textPreview = text ? text.substring(0, 50) + (text.length > 50 ? '...' : '') : '';
                    
                    const childInfo = {
                        tagName: tagName,
                        selector: tagName + id + className,
                        text: textPreview,
                        childCount: child.children.length
                    };
                    
                    // 递归获取子元素
                    if (child.children.length > 0 && depth < maxDepth) {
                        childInfo.children = analyzeChildStructure(child, depth + 1, maxDepth);
                    }
                    
                    result.push(childInfo);
                }
                
                return result;
            }
            
            // 处理每个列表项，提取完整信息
            const itemsInfo = listItems.map((item, index) => {
                // 提取文本内容
                const originalText = item.innerText || item.textContent || '';
                
                // 获取列表项的HTML结构
                const itemHTML = item.outerHTML;
                
                // 获取列表项的CSS选择器
                const itemSelector = getCssSelector(item);
                
                // 查找列表项中的可点击元素
                const clickableElements = findClickableElements(item);
                
                // 创建子元素信息
                const childStructure = analyzeChildStructure(item);
                
                return {
                    index: index,
                    originalText: originalText,
                    htmlPreview: itemHTML.length > 500 ? itemHTML.substring(0, 500) + '...' : itemHTML,
                    selector: itemSelector,
                    element: {
                        tagName: item.tagName.toLowerCase(),
                        id: item.id || '',
                        className: item.className || '',
                        attributes: getElementAttributes(item)
                    },
                    childStructure: childStructure,
                    clickableElements: clickableElements.map((el, idx) => ({
                        index: idx,
                        type: el.tagName.toLowerCase(),
                        text: (el.innerText || el.textContent || '').substring(0, 100),
                        selector: getCssSelector(el),
                        attributes: getElementAttributes(el)
                    }))
                };
            });
            
            return {
                found: true,
                listElement: true,
                listItems: true,
                totalItems: listItems.length,
                itemsInfo: itemsInfo,
                isStandardList: true,
                listType: tagName
            };
        }
        """
        
        print(f"\n正在分析选中的列表...")
        
        # 根据列表是否在iframe中选择不同的执行方式
        if in_iframe:
            # 获取iframe信息和句柄
            iframe_info = selected_list['iframe']
            iframe_handles = browser_tool._async_loop.run_until_complete(
                browser_tool.context.pages[page_index].query_selector_all('iframe')
            )
            
            if iframe_info['index'] < len(iframe_handles):
                iframe_handle = iframe_handles[iframe_info['index']]
                content_frame = browser_tool._async_loop.run_until_complete(iframe_handle.content_frame())
                
                if content_frame:
                    list_result = browser_tool._async_loop.run_until_complete(
                        content_frame.evaluate(get_list_items_js, {'listSelector': list_selector})
                    )
                else:
                    print(f"无法获取iframe的内容")
                    return
            else:
                print(f"无法获取iframe (索引: {iframe_info['index']})")
                return
        else:
            # 主页面中的列表
            list_result = browser_tool._async_loop.run_until_complete(
                browser_tool.context.pages[page_index].evaluate(get_list_items_js, {'listSelector': list_selector})
            )
        
        # 检查是否成功获取列表项
        if not list_result.get('found', False) or not list_result.get('listItems', False):
            print(f"无法获取列表项: {list_result.get('message', '未知错误')}")
            return
        
        # 显示列表项信息
        items_info = list_result.get('itemsInfo', [])
        total_items = list_result.get('totalItems', 0)
        list_type = list_result.get('listType', '')
        is_standard_list = list_result.get('isStandardList', False)
        
        print(f"\n列表 '{list_selector}' 共有 {total_items} 个列表项，显示全部 {len(items_info)} 项:")
        print(f"列表类型: {list_type}" + (" (标准列表)" if is_standard_list else ""))
        
        # 使用提供的显示模式或默认值
        if display_mode not in ['1', '2', '3', '4']:
            display_mode = '1'  # 默认使用简洁模式
        
        # 循环显示所有列表项
        for item in items_info:
            item_index = item['index']
            
            # 获取元素基本信息
            element_info = item.get('element', {})
            element_tag = element_info.get('tagName', 'unknown')
            element_id = f"#{element_info.get('id')}" if element_info.get('id') else ""
            element_class = f".{element_info.get('className')}" if element_info.get('className') else ""
            
            # 获取结构信息
            structure = item.get('structure', {})
            child_elements = structure.get('childElementCount', 0)
            child_nodes = structure.get('childNodesCount', 0)
            text_nodes = structure.get('textNodesCount', 0)
            depth = structure.get('depth', 0)
            
            # 获取子元素结构
            child_structure = item.get('childStructure', [])
            
            # 原始文本
            original_text = item.get('originalText', '').replace('\n', ' ').strip()
            
            # 使用更清晰的序号标识列表项
            item_number = f"【项目{item_index+1}】"
            
            # 根据显示模式调整输出
            if display_mode == "1":  # 简洁模式
                # 简化显示，只显示基本文本
                if len(original_text) > 100:
                    original_text = original_text[:97] + "..."
                
                print(f"\n{item_number} {element_tag}{element_id}{element_class} - {original_text}")
                print(f"    子元素: {child_elements}个, 文本节点: {text_nodes}个, 深度: {depth}")
                
            elif display_mode == "2":  # 标准模式
                # 标准显示，包含元素基本信息和部分子元素
                print(f"\n{item_number} {element_tag}{element_id}{element_class}")
                
                # 显示原始文本
                if original_text:
                    if len(original_text) > 100:
                        original_text = original_text[:97] + "..."
                    print(f"    文本: {original_text}")
                
                # 显示子元素信息
                print(f"    结构: {child_elements}个子元素, {text_nodes}个文本节点, 深度: {depth}")
                
                # 显示子元素
                if child_structure and len(child_structure) > 0:
                    print(f"    子元素 ({len(child_structure)}个):")
                    for i, child in enumerate(child_structure[:5]):  # 显示前5个
                        child_text = child.get('text', '')
                        child_selector = child.get('selector', '')
                        # 使用清晰的嵌套标号
                        child_number = f"{item_index+1}.{i+1}"
                        print(f"      • 子元素[{child_number}]: {child_selector}: '{child_text}'")
                    
                    if len(child_structure) > 5:
                        print(f"      ... 还有 {len(child_structure) - 5} 个子元素未显示")
                else:
                    print("    无子元素")
            
            elif display_mode == "3":  # 详细模式
                # 详细显示，包含完整信息
                print(f"\n{item_number} {element_tag}{element_id}{element_class}")
                
                # 显示选择器
                print(f"    选择器: {item.get('selector', '')}")
                
                # 显示原始文本
                if original_text:
                    print(f"    文本: {original_text}")
                
                # 显示DOM结构信息
                print(f"    DOM结构: {child_elements}个子元素, {child_nodes}个子节点")
                print(f"    文本节点: {text_nodes}个, 元素节点: {structure.get('elementNodesCount', 0)}个, 深度: {depth}")
                
                # 显示HTML预览
                html_preview = item.get('htmlPreview', '')
                if html_preview:
                    print(f"    HTML预览: {html_preview[:150]}...")
                
                # 显示子元素
                if child_structure and len(child_structure) > 0:
                    print(f"    子元素 ({len(child_structure)}个):")
                    for i, child in enumerate(child_structure):
                        child_text = child.get('text', '')
                        child_selector = child.get('selector', '')
                        child_count = child.get('childCount', 0)
                        # 更清晰的嵌套编号
                        child_number = f"{item_index+1}.{i+1}"
                        print(f"      • 子元素[{child_number}]: {child_selector}: '{child_text}' (子元素: {child_count}个)")
                else:
                    print("    无子元素")
                
                # 显示可点击元素信息
                clickable_elements = item.get('clickableElements', [])
                if clickable_elements:
                    print(f"    可点击元素 ({len(clickable_elements)}个):")
                    for clickable in clickable_elements:
                        clickable_text = clickable['text'].replace('\n', ' ').strip() or f"[{clickable['type']}元素]"
                        print(f"      [{clickable['index'] + 1}] {clickable['type']}: '{clickable_text}'")
                        print(f"          选择器: {clickable['selector']}")
                else:
                    print("    无可点击元素")
            
            elif display_mode == "4":  # 层次结构模式
                print(f"\n{item_number} {element_tag}{element_id}{element_class}")
                
                # 层次结构展示子元素
                if child_structure and len(child_structure) > 0:
                    print(f"    结构树 ({len(child_structure)}个顶级子元素):")
                    
                    def print_tree(nodes, indent=6, prefix=""):
                        for i, node in enumerate(nodes):
                            tag = node.get('tagName', '')
                            selector = node.get('selector', '')
                            text = node.get('text', '')
                            child_count = node.get('childCount', 0)
                            
                            # 缩进显示层级结构，使用带层级的编号
                            # 如果前缀存在，使用"前缀.序号"，否则使用序号
                            node_number = f"{prefix}{i+1}" if prefix else f"{item_index+1}.{i+1}"
                            
                            indent_str = " " * indent
                            line = f"{indent_str}• [{node_number}] {selector}"
                            if text:
                                line += f": '{text}'"
                            if child_count > 0:
                                line += f" ({child_count}个子元素)"
                            print(line)
                            
                            # 递归显示子节点，传递当前节点编号作为前缀
                            children = node.get('children', [])
                            if children and len(children) > 0:
                                print_tree(children, indent + 4, prefix=f"{node_number}.")
                    
                    # 初始调用不传递前缀
                    print_tree(child_structure)
                else:
                    print("    无子元素或结构")
            
            # 在简洁和标准模式下显示可点击元素的基本信息
            if display_mode in ["1", "2"]:
                clickable_elements = item.get('clickableElements', [])
                if clickable_elements:
                    print(f"    包含 {len(clickable_elements)} 个可点击元素")
        
        # 检查是否需要自动点击
        if not auto_click:
            print("\n提示：使用auto_click=True和相关参数来自动点击列表项")
            return {
                "success": True, 
                "message": "列表项分析完成，使用auto_click=True来进行点击操作",
                "items_info": items_info,
                "total_items": len(items_info)
            }
        
        # 验证要点击的列表项索引
        if item_index is None:
            print("错误: 必须提供item_index参数来指定要点击的列表项")
            return
            
        try:
            selected_item_index = item_index - 1
            if selected_item_index < 0 or selected_item_index >= len(items_info):
                print(f"无效的序号，有效范围: 1-{len(items_info)}")
                return
                
            selected_item = items_info[selected_item_index]
            clickable_elements = selected_item['clickableElements']
            
            if not clickable_elements:
                print("该列表项没有可点击元素，将尝试点击列表项本身")
                selector = selected_item['selector']
            else:
                if len(clickable_elements) == 1:
                    print(f"列表项中只有1个可点击元素，将直接点击该元素")
                    selector = clickable_elements[0]['selector']
                else:
                    # 该列表项包含多个可点击元素，需要指定索引
                    if clickable_index is None:
                        print(f"该列表项包含{len(clickable_elements)}个可点击元素，必须提供clickable_index参数")
                        for i, element in enumerate(clickable_elements):
                            element_type = element['type']
                            element_text = element['text'].replace('\n', ' ').strip() or f"[{element_type}元素]"
                            print(f"[{i+1}] <{element_type}>: '{element_text}'")
                        return
                    
                    # 验证可点击元素索引
                    selected_clickable_index = clickable_index - 1
                    if selected_clickable_index < 0 or selected_clickable_index >= len(clickable_elements):
                        print(f"无效的可点击元素序号，有效范围: 1-{len(clickable_elements)}")
                        return
                    selector = clickable_elements[selected_clickable_index]['selector']
            
            # 执行点击操作
            print(f"\n正在点击指定元素... (选择器: {selector})")
            
            # 检查是否在iframe中
            if in_iframe:
                iframe_info = selected_list['iframe']
                print(f"注意: 元素位于iframe '{iframe_info['name']}' 中，将使用直接方法点击")
                
                # 新的直接点击方法
                direct_click_result = direct_click_in_iframe(
                    browser_tool=browser_tool,
                    page_index=page_index,
                    iframe_index=iframe_info['index'],
                    selector=selector,
                    wait_for_navigation=wait_for_navigation
                )
                
                if direct_click_result['success']:
                    print(f"在iframe中点击成功!")
                    return
                    
                print("直接点击方法失败，尝试其他方法...")
                
                try:
                    # 尝试使用更简单的选择器 - 根据元素类型和文本内容
                    if clickable_elements and len(clickable_elements) > 0:
                        simple_query = None
                        
                        # 选择一个更简单的选择方式
                        for element in clickable_elements:
                            if element['type'] == 'button' and element['text']:
                                text = element['text'].replace("'", "\\'").strip()
                                simple_query = f"button:has-text('{text}')"
                                break
                            elif element['type'] == 'a' and element['text']:
                                text = element['text'].replace("'", "\\'").strip()
                                simple_query = f"a:has-text('{text}')"
                                break
                        
                        if simple_query:
                            print(f"使用文本选择器: {simple_query}")
                            # 直接在内容框架中点击
                            click_succeeded = False
                            try:
                                # 尝试定位并点击元素
                                element_handle = browser_tool._async_loop.run_until_complete(
                                    content_frame.query_selector(simple_query)
                                )
                                if element_handle:
                                    browser_tool._async_loop.run_until_complete(element_handle.click())
                                    click_succeeded = True
                                    print("使用文本选择器成功点击元素")
                                    return
                                else:
                                    print(f"使用文本选择器未找到元素: {simple_query}")
                                    
                                # 使用JavaScript尝试查找和点击元素
                                print("尝试使用JavaScript点击...")
                                js_result = browser_tool._async_loop.run_until_complete(
                                    content_frame.evaluate(f"""
                                        () => {{
                                            const elements = Array.from(document.querySelectorAll('button, a'));
                                            const targetElement = elements.find(el => 
                                                el.innerText && el.innerText.includes('{text}')
                                            );
                                            if (targetElement) {{
                                                targetElement.click();
                                                return true;
                                            }}
                                            return false;
                                        }}
                                    """)
                                )
                                
                                # 等待可能的导航
                                if wait_for_navigation:
                                    print("等待页面可能的导航...")
                                    try:
                                        browser_tool._async_loop.run_until_complete(
                                            browser_tool.context.pages[page_index].wait_for_navigation(timeout=5000)
                                        )
                                    except:
                                        pass
                                
                                if js_result:
                                    print("使用JavaScript成功点击元素")
                                    return
                                else:
                                    print("使用JavaScript无法点击元素")
                            except Exception as e:
                                print(f"使用文本选择器点击时出错: {str(e)}")
                    
                    # 尝试直接点击元素
                    try:
                        element_handle = browser_tool._async_loop.run_until_complete(
                            content_frame.query_selector(selector)
                        )
                        if element_handle:
                            browser_tool._async_loop.run_until_complete(element_handle.click())
                            print("成功在iframe中点击元素!")
                            return
                        else:
                            print(f"在iframe中无法获取元素句柄: {selector}")
                    except Exception as click_error:
                        print(f"在iframe中点击元素时出错: {str(click_error)}")
                        
                except Exception as iframe_error:
                    print(f"处理iframe时出错: {str(iframe_error)}")
                
                print("所有iframe内点击方法都失败，尝试常规点击...")
            
            # 执行常规点击
            click_result = browser_tool.click_element(
                page_index=page_index,
                element_selector=selector,
                click_type='click',
                wait_for_navigation=wait_for_navigation
            )
            
            if click_result['success']:
                print(f"点击成功!")
                print(f"页面标题: {click_result['title']}")
                print(f"页面URL: {click_result['url']}")
            else:
                print(f"点击失败: {click_result['message']}")
                
        except ValueError:
            print("输入错误，必须是整数")
            return
                
    except Exception as e:
        import traceback
        print(f"处理列表元素时出错: {str(e)}")
        traceback.print_exc()
        return