import pathlib
import sys
import time

current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

current_dir = pathlib.Path(__file__).parent
root_dir = current_dir.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# 导入依赖的函数
from .direct_click_in_iframe import direct_click_in_iframe

def find_and_click_role_list_items(browser_tool, page_index=None, include_iframes=None,
                                   container_role=None, item_role=None, sub_item_role=None,
                                   container_index=None, item_index=None, operation_type=None, 
                                   wait_for_navigation=True):
    """通过role属性查找并点击嵌套列表项（如group-listitem-geek-item结构）
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 要查找列表的页面序号，默认0
        include_iframes: 是否在iframe中查找，默认True
        container_role: 容器元素的role (例如: group)，必需
        item_role: 列表项元素的role (例如: listitem)，必需
        sub_item_role: 子项元素的role (例如: geek-item，可选)
        container_index: 要选择的容器序号 (1-based)，如果为None则仅显示信息
        item_index: 要选择的列表项序号 (1-based)，如果为None则仅显示信息
        operation_type: 操作类型 (1-based索引)，如果为None则仅显示信息
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
    
    # 检查必需的参数
    if container_role is None:
        print("错误: 必须提供container_role参数")
        return
    
    if item_role is None:
        print("错误: 必须提供item_role参数")
        return
    
    print(f"\n正在页面 {page_index} 中查找 role={container_role} 容器下的 role={item_role} 列表项...")
    if sub_item_role:
        print(f"同时会查找列表项下的 role={sub_item_role} 子项")
    
    # 创建JavaScript查找代码
    find_role_lists_js = """
    (params) => {
        const containerRole = params.containerRole;
        const itemRole = params.itemRole;
        const subItemRole = params.subItemRole;
        
        // 获取CSS选择器函数
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
                    // 确保className是字符串类型
                    let classValue = '';
                    if (typeof element.className === 'string') {
                        classValue = element.className;
                    } else if (element.className.baseVal !== undefined) {
                        classValue = element.className.baseVal;
                    }
                    
                    const classes = classValue.split(/\\s+/).filter(Boolean);
                    if (classes.length > 0) {
                        selector += '.' + classes.join('.');
                    }
                }
                
                // 添加role属性到选择器
                const role = element.getAttribute('role');
                if (role) {
                    selector += `[role="${role}"]`;
                }
                
                let sibling = element;
                let index = 1;
                while (sibling = sibling.previousElementSibling) {
                    if (sibling.nodeName.toLowerCase() === selector.split('.')[0].split('[')[0]) {
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
        
        // 查找所有具有指定role的容器
        const containers = Array.from(document.querySelectorAll(`[role="${containerRole}"]`));
        
        if (containers.length === 0) {
            return { 
                found: false, 
                message: `未找到role为${containerRole}的容器元素` 
            };
        }
        
        const listContainers = [];
        
        // 检查每个容器
        for (const container of containers) {
            // 查找容器内的列表项
            const listItems = Array.from(container.querySelectorAll(`[role="${itemRole}"]`));
            
            if (listItems.length > 0) {
                // 收集容器信息
                const containerInfo = {
                    role: containerRole,
                    selector: getCssSelector(container),
                    childCount: listItems.length,
                    position: container.getBoundingClientRect(),
                    isVisible: container.offsetParent !== null && 
                              container.offsetWidth > 0 && 
                              container.offsetHeight > 0,
                    id: container.id || '',
                    className: container.className || '',
                    tagName: container.tagName.toLowerCase(),
                    attributes: {}
                };
                
                // 收集所有属性
                Array.from(container.attributes).forEach(attr => {
                    containerInfo.attributes[attr.name] = attr.value;
                });
                
                // 收集列表项信息
                const items = [];
                for (const item of listItems) {
                    // 基本列表项信息
                    const itemInfo = {
                        role: itemRole,
                        selector: getCssSelector(item),
                        text: (item.innerText || item.textContent || '').substring(0, 100),
                        position: item.getBoundingClientRect(),
                        isVisible: item.offsetParent !== null && 
                                  item.offsetWidth > 0 && 
                                  item.offsetHeight > 0,
                        id: item.id || '',
                        className: item.className || '',
                        tagName: item.tagName.toLowerCase(),
                        attributes: {},
                        key: item.getAttribute('key') || ''
                    };
                    
                    // 收集所有属性
                    Array.from(item.attributes).forEach(attr => {
                        itemInfo.attributes[attr.name] = attr.value;
                    });
                    
                    // 如果有子项role，查找子项
                    if (subItemRole) {
                        const subItems = Array.from(item.querySelectorAll(`[role="${subItemRole}"]`));
                        if (subItems.length > 0) {
                            const subItemsInfo = [];
                            
                            for (const subItem of subItems) {
                                const subItemInfo = {
                                    role: subItemRole,
                                    selector: getCssSelector(subItem),
                                    text: (subItem.innerText || subItem.textContent || '').substring(0, 100),
                                    position: subItem.getBoundingClientRect(),
                                    isVisible: subItem.offsetParent !== null && 
                                              subItem.offsetWidth > 0 && 
                                              subItem.offsetHeight > 0,
                                    id: subItem.id || '',
                                    className: subItem.className || '',
                                    tagName: subItem.tagName.toLowerCase(),
                                    attributes: {}
                                };
                                
                                // 收集所有属性
                                Array.from(subItem.attributes).forEach(attr => {
                                    subItemInfo.attributes[attr.name] = attr.value;
                                });
                                
                                // 查找可点击元素
                                const clickableElements = findClickableElements(subItem);
                                if (clickableElements.length > 0) {
                                    subItemInfo.hasClickable = true;
                                    subItemInfo.clickableCount = clickableElements.length;
                                    
                                    // 收集前几个可点击元素的信息
                                    const clickableInfo = clickableElements.slice(0, 5).map(el => {
                                        return {
                                            tagName: el.tagName.toLowerCase(),
                                            text: (el.innerText || el.textContent || '').substring(0, 50),
                                            selector: getCssSelector(el)
                                        };
                                    });
                                    
                                    subItemInfo.clickableElements = clickableInfo;
                                } else {
                                    subItemInfo.hasClickable = false;
                                }
                                
                                subItemsInfo.push(subItemInfo);
                            }
                            
                            itemInfo.subItems = subItemsInfo;
                            itemInfo.subItemCount = subItems.length;
                        }
                    }
                    
                    // 查找可点击元素
                    const clickableElements = findClickableElements(item);
                    if (clickableElements.length > 0) {
                        itemInfo.hasClickable = true;
                        itemInfo.clickableCount = clickableElements.length;
                        
                        // 收集前几个可点击元素的信息
                        const clickableInfo = clickableElements.slice(0, 5).map(el => {
                            return {
                                tagName: el.tagName.toLowerCase(),
                                text: (el.innerText || el.textContent || '').substring(0, 50),
                                selector: getCssSelector(el)
                            };
                        });
                        
                        itemInfo.clickableElements = clickableInfo;
                    } else {
                        itemInfo.hasClickable = false;
                    }
                    
                    items.push(itemInfo);
                }
                
                containerInfo.items = items;
                listContainers.push(containerInfo);
            }
        }
        
        if (listContainers.length === 0) {
            return { 
                found: false, 
                message: `未找到包含role为${itemRole}列表项的${containerRole}容器` 
            };
        }
        
        // 按列表项数量排序
        listContainers.sort((a, b) => b.childCount - a.childCount);
        
        return {
            found: true,
            containers: listContainers,
            count: listContainers.length
        };
    }
    """
    
    try:
        # 执行JavaScript获取列表信息
        main_result = browser_tool._async_loop.run_until_complete(
            browser_tool.context.pages[page_index].evaluate(find_role_lists_js, {
                'containerRole': container_role,
                'itemRole': item_role,
                'subItemRole': sub_item_role
            })
        )
        
        main_containers = []
        if main_result.get('found', False):
            main_containers = main_result.get('containers', [])
        else:
            print(f"主页面中未找到匹配的列表: {main_result.get('message', '')}")
        
        iframe_containers = []
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
                        iframe_result = browser_tool._async_loop.run_until_complete(
                            content_frame.evaluate(find_role_lists_js, {
                                'containerRole': container_role,
                                'itemRole': item_role,
                                'subItemRole': sub_item_role
                            })
                        )
                        
                        if iframe_result.get('found', False):
                            iframe_containers_data = iframe_result.get('containers', [])
                            
                            # 将iframe信息添加到每个容器
                            for container in iframe_containers_data:
                                container['iframe'] = {
                                    'id': iframe_id,
                                    'name': iframe_name,
                                    'src': iframe_src,
                                    'index': i
                                }
                            
                            iframe_containers.extend(iframe_containers_data)
                            print(f"在iframe '{iframe_name}' 中找到 {len(iframe_containers_data)} 个列表容器！")
                        
                    except Exception as e:
                        print(f"处理iframe '{iframe_id}' 时出错: {str(e)}")
                    finally:
                        # 释放iframe句柄
                        browser_tool._async_loop.run_until_complete(iframe_handle.dispose())
        
        # 合并结果
        all_containers = main_containers + iframe_containers
        
        if not all_containers:
            print(f"未找到基于role={container_role}和role={item_role}的列表结构")
            return
        
        # 显示找到的列表容器
        print(f"\n找到 {len(all_containers)} 个匹配的列表容器:")
        
        for i, container in enumerate(all_containers):
            # 容器基本信息
            in_iframe = 'iframe' in container
            iframe_info = f" [来自iframe: {container['iframe']['name']}]" if in_iframe else ""
            list_count = container['childCount']
            
            # 显示容器信息
            print(f"\n【容器{i+1}】 <{container['tagName']}> role=\"{container['role']}\" {iframe_info}")
            print(f"  列表项数量: {list_count}")
            print(f"  选择器: {container['selector']}")
            
            # 显示几个列表项的简要信息
            if list_count > 0:
                preview_count = min(3, list_count)
                print(f"  列表项预览 (显示前{preview_count}项):")
                
                for j in range(preview_count):
                    item = container['items'][j]
                    item_text = item['text'].replace('\n', ' ').strip()
                    if len(item_text) > 50:
                        item_text = item_text[:47] + "..."
                    
                    print(f"    • 项目[{j+1}] {item['tagName']} role=\"{item['role']}\" key=\"{item['key']}\"")
                    print(f"      文本: \"{item_text}\"")
                    
                    # 如果有子项，显示子项信息
                    if 'subItems' in item and item['subItems']:
                        sub_count = len(item['subItems'])
                        print(f"      包含 {sub_count} 个子项 (role=\"{sub_item_role}\")")
                
                if list_count > preview_count:
                    print(f"    • ... 还有 {list_count - preview_count} 个列表项未显示")
        
        # 检查是否提供了容器索引
        if container_index is None:
            print("请使用container_index参数指定要操作的容器序号 (1-based)")
            return {
                "success": True,
                "message": "找到容器，请指定container_index参数来操作特定容器",
                "containers": all_containers,
                "total_containers": len(all_containers)
            }
        
        # 验证容器索引
        selected_container_index = container_index - 1
        if selected_container_index < 0 or selected_container_index >= len(all_containers):
            print(f"无效的容器序号，有效范围: 1-{len(all_containers)}")
            return
            
        # 获取选中的容器
        selected_container = all_containers[selected_container_index]
        container_in_iframe = 'iframe' in selected_container
        
        # 显示选中容器中的所有列表项
        items = selected_container['items']
        print(f"\n容器 {selected_container_index+1} 中的列表项:")
        
        for i, item in enumerate(items):
            # 基本信息
            item_text = item['text'].replace('\n', ' ').strip()
            if len(item_text) > 70:
                item_text = item_text[:67] + "..."
                
            # 是否可点击
            clickable_info = ""
            if item.get('hasClickable', False):
                clickable_info = f" [✓可点击, {item.get('clickableCount', 0)}个可点击元素]"
            
            # 是否有子项
            subitem_info = ""
            if 'subItems' in item and item['subItems']:
                subitem_info = f" [✓包含{len(item['subItems'])}个子项]"
            
            print(f"\n【项目{i+1}】 <{item['tagName']}> role=\"{item['role']}\" key=\"{item['key']}\"")
            print(f"  文本: \"{item_text}\"")
            print(f"  选择器: {item['selector']}")
            print(f"  状态: {clickable_info}{subitem_info}")
            
            # 如果有子项，显示子项信息
            if 'subItems' in item and item['subItems'] and len(item['subItems']) > 0:
                print("  子项:")
                for j, subitem in enumerate(item['subItems']):
                    subitem_text = subitem['text'].replace('\n', ' ').strip()
                    if len(subitem_text) > 50:
                        subitem_text = subitem_text[:47] + "..."
                    
                    # 子项是否可点击
                    sub_clickable = ""
                    if subitem.get('hasClickable', False):
                        sub_clickable = f" [✓可点击, {subitem.get('clickableCount', 0)}个可点击元素]"
                    
                    print(f"    • 子项[{j+1}] <{subitem['tagName']}> role=\"{subitem['role']}\"{sub_clickable}")
                    print(f"      文本: \"{subitem_text}\"")
        
        # 检查是否提供了列表项索引
        if item_index is None:
            print("请使用item_index参数指定要操作的列表项序号 (1-based)")
            return {
                "success": True,
                "message": "找到列表项，请指定item_index参数来操作特定列表项",
                "items": items,
                "total_items": len(items)
            }
        
        # 验证列表项索引
        selected_item_index = item_index - 1
        if selected_item_index < 0 or selected_item_index >= len(items):
            print(f"无效的列表项序号，有效范围: 1-{len(items)}")
            return
        
        # 获取选中的列表项
        selected_item = items[selected_item_index]
        
        # 设置操作选项
        operations = ["点击整个列表项"]
        
        # 如果列表项有可点击元素，添加相应选项
        if selected_item.get('hasClickable', False) and 'clickableElements' in selected_item:
            for i, clickable in enumerate(selected_item['clickableElements']):
                text = clickable['text'] or f"<{clickable['tagName']}>"
                operations.append(f"点击元素: {text}")
        
        # 如果列表项有子项，添加子项操作选项
        has_subitems = 'subItems' in selected_item and selected_item['subItems']
        if has_subitems:
            for i, subitem in enumerate(selected_item['subItems']):
                text = subitem['text'] or f"<{subitem['tagName']}>"
                operations.append(f"点击子项: {text}")
        
        # 检查是否提供了操作类型索引
        if operation_type is None:
            print("请使用operation_type参数指定要执行的操作类型 (1-based)")
            print("可用操作:")
            for i, op in enumerate(operations):
                print(f"{i+1}. {op}")
            return {
                "success": True,
                "message": "找到操作选项，请指定operation_type参数来执行特定操作",
                "operations": operations,
                "total_operations": len(operations)
            }
        
        # 验证操作类型索引
        operation_index = operation_type - 1
        if operation_index < 0 or operation_index >= len(operations):
            print(f"无效的操作类型序号，有效范围: 1-{len(operations)}")
            return
        
        try:
            
            # 执行操作
            if operation_index == 0:
                # 点击整个列表项
                selector = selected_item['selector']
                
                if container_in_iframe:
                    # 在iframe中点击
                    iframe_index = selected_container['iframe']['index']
                    print(f"\n在iframe中点击列表项 {selected_item_index+1}...")
                    
                    result = direct_click_in_iframe(
                        browser_tool, 
                        page_index, 
                        iframe_index, 
                        selector,
                        wait_for_navigation
                    )
                    
                    if result['success']:
                        print("点击成功!")
                    else:
                        print(f"点击失败: {result['message']}")
                else:
                    # 在主页面中点击
                    print(f"\n点击列表项 {selected_item_index+1}...")
                    
                    click_result = browser_tool.click_element(
                        page_index=page_index,
                        element_selector=selector,
                        click_type='click',
                        wait_for_navigation=wait_for_navigation
                    )
                    
                    if click_result['success']:
                        print("点击成功!")
                        if wait_for_navigation:
                            print(f"页面标题: {click_result['title']}")
                            print(f"页面URL: {click_result['url']}")
                    else:
                        print(f"点击失败: {click_result['message']}")
            
            elif operation_index < len(selected_item.get('clickableElements', [])) + 1:
                # 点击列表项中的可点击元素
                clickable_index = operation_index - 1
                clickable = selected_item['clickableElements'][clickable_index]
                selector = clickable['selector']
                
                if container_in_iframe:
                    # 在iframe中点击
                    iframe_index = selected_container['iframe']['index']
                    print(f"\n在iframe中点击列表项 {selected_item_index+1} 中的元素 {clickable['text']}...")
                    
                    result = direct_click_in_iframe(
                        browser_tool, 
                        page_index, 
                        iframe_index, 
                        selector,
                        wait_for_navigation
                    )
                    
                    if result['success']:
                        print("点击成功!")
                    else:
                        print(f"点击失败: {result['message']}")
                else:
                    # 在主页面中点击
                    print(f"\n点击列表项 {selected_item_index+1} 中的元素 {clickable['text']}...")
                    
                    click_result = browser_tool.click_element(
                        page_index=page_index,
                        element_selector=selector,
                        click_type='click',
                        wait_for_navigation=wait_for_navigation
                    )
                    
                    if click_result['success']:
                        print("点击成功!")
                        if wait_for_navigation:
                            print(f"页面标题: {click_result['title']}")
                            print(f"页面URL: {click_result['url']}")
                    else:
                        print(f"点击失败: {click_result['message']}")
            
            else:
                # 点击子项
                subitem_index = operation_index - 1 - len(selected_item.get('clickableElements', []))
                subitem = selected_item['subItems'][subitem_index]
                selector = subitem['selector']
                
                if container_in_iframe:
                    # 在iframe中点击
                    iframe_index = selected_container['iframe']['index']
                    print(f"\n在iframe中点击列表项 {selected_item_index+1} 的子项 {subitem_index+1}...")
                    
                    result = direct_click_in_iframe(
                        browser_tool, 
                        page_index, 
                        iframe_index, 
                        selector,
                        wait_for_navigation
                    )
                    
                    if result['success']:
                        print("点击成功!")
                    else:
                        print(f"点击失败: {result['message']}")
                else:
                    # 在主页面中点击
                    print(f"\n点击列表项 {selected_item_index+1} 的子项 {subitem_index+1}...")
                    
                    click_result = browser_tool.click_element(
                        page_index=page_index,
                        element_selector=selector,
                        click_type='click',
                        wait_for_navigation=wait_for_navigation
                    )
                    
                    if click_result['success']:
                        print("点击成功!")
                        if wait_for_navigation:
                            print(f"页面标题: {click_result['title']}")
                            print(f"页面URL: {click_result['url']}")
                    else:
                        print(f"点击失败: {click_result['message']}")
            
        except ValueError:
            print("输入错误，必须是整数")
            return
    
    except Exception as e:
        import traceback
        print(f"执行过程中出错: {str(e)}")
        print(traceback.format_exc()) 