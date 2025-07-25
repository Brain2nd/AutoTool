import json
import re

def extract_position_info(browser_tool, page_index):
    """
    提取候选人简历中的职位信息、薪资和期望
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 页面索引
    
    Returns:
        dict: 包含职位、薪资和期望信息的字典
    """
    print("\n正在提取职位信息...")
    
    # 获取页面
    page = browser_tool.context.pages[page_index]
    
    # 定义提取JavaScript代码
    extract_js = """
    () => {
        // 提取职位信息
        const positionData = {};
        
        // 查找职位名称 - position-name类
        const positionNameElem = document.querySelector('.position-name');
        if (positionNameElem) {
            positionData.position = positionNameElem.textContent.trim();
        } else {
            positionData.position = "未找到职位名称";
        }
        
        // 查找所有position-item类元素
        const positionItems = document.querySelectorAll('.position-item');
        positionItems.forEach(item => {
            // 获取label
            const labelElem = item.querySelector('.label');
            if (!labelElem) return;
            
            const label = labelElem.textContent.trim();
            
            // 获取value
            const valueElem = item.querySelector('.value');
            if (!valueElem) return;
            
            // 根据label分类处理
            if (label.includes('沟通职位')) {
                positionData.communicated_position = valueElem.textContent.trim();
                // 删除"更换职位"等后缀
                positionData.communicated_position = positionData.communicated_position.replace(/\s+更换职位$/, '').trim();
            } else if (label.includes('期望')) {
                // 捕获完整的期望内容，包括可能的薪资信息
                const fullContent = valueElem.innerHTML;
                positionData.expectation_full = valueElem.textContent.trim();
                
                // 尝试解析薪资
                const salaryElement = valueElem.querySelector('.high-light-orange');
                if (salaryElement) {
                    positionData.salary = salaryElement.textContent.trim();
                }
                
                // 尝试提取期望职位
                const jobValueElem = valueElem.classList.contains('value') && 
                                     valueElem.classList.contains('job') ? 
                                     valueElem : null;
                if (jobValueElem) {
                    // 获取纯文本内容，移除薪资部分
                    let jobText = jobValueElem.textContent.trim();
                    // 如果存在薪资信息，尝试将其从文本中分离
                    if (salaryElement) {
                        jobText = jobText.replace(salaryElement.textContent, '').trim();
                    }
                    positionData.job_expectation = jobText;
                }
            }
        });
        
        // 如果在主页面找不到，尝试在iframe中寻找
        if (!positionData.position || positionData.position === "未找到职位名称") {
            const iframes = document.querySelectorAll('iframe');
            for (let i = 0; i < iframes.length; i++) {
                try {
                    const frameDoc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                    
                    // 在iframe中查找职位名称
                    const framePositionNameElem = frameDoc.querySelector('.position-name');
                    if (framePositionNameElem) {
                        positionData.position = framePositionNameElem.textContent.trim();
                    }
                    
                    // 在iframe中查找所有position-item类元素
                    const framePositionItems = frameDoc.querySelectorAll('.position-item');
                    framePositionItems.forEach(item => {
                        const labelElem = item.querySelector('.label');
                        if (!labelElem) return;
                        
                        const label = labelElem.textContent.trim();
                        
                        const valueElem = item.querySelector('.value');
                        if (!valueElem) return;
                        
                        if (label.includes('沟通职位')) {
                            positionData.communicated_position = valueElem.textContent.trim();
                            // 删除"更换职位"等后缀
                            positionData.communicated_position = positionData.communicated_position.replace(/\s+更换职位$/, '').trim();
                        } else if (label.includes('期望')) {
                            const fullContent = valueElem.innerHTML;
                            positionData.expectation_full = valueElem.textContent.trim();
                            
                            const salaryElement = valueElem.querySelector('.high-light-orange');
                            if (salaryElement) {
                                positionData.salary = salaryElement.textContent.trim();
                            }
                            
                            const jobValueElem = valueElem.classList.contains('value') && 
                                                valueElem.classList.contains('job') ? 
                                                valueElem : null;
                            if (jobValueElem) {
                                let jobText = jobValueElem.textContent.trim();
                                if (salaryElement) {
                                    jobText = jobText.replace(salaryElement.textContent, '').trim();
                                }
                                positionData.job_expectation = jobText;
                            }
                        }
                    });
                    
                    // 如果在这个iframe中找到了数据，终止循环
                    if (positionData.position && positionData.position !== "未找到职位名称") {
                        break;
                    }
                } catch (e) {
                    // 忽略跨域错误
                    console.log('无法访问iframe内容:', e);
                }
            }
        }
        
        return positionData;
    }
    """
    
    try:
        # 在主页面执行提取
        main_result = browser_tool._async_loop.run_until_complete(
            page.evaluate(extract_js)
        )
        
        if main_result:
            print(f"主页面提取结果: {json.dumps(main_result, ensure_ascii=False)}")
            
            # 检查是否有必要的数据
            if main_result.get('position') != "未找到职位名称" or main_result.get('communicated_position'):
                return main_result
        
        # 如果主页面没有提取到足够的信息，尝试在iframe中查找
        iframe_handles = browser_tool._async_loop.run_until_complete(
            page.query_selector_all('iframe')
        )
        
        if iframe_handles:
            print(f"发现 {len(iframe_handles)} 个iframe，尝试提取信息...")
            
            for i, iframe_handle in enumerate(iframe_handles):
                try:
                    iframe_name = browser_tool._async_loop.run_until_complete(
                        iframe_handle.get_attribute('name')
                    ) or f"iframe-{i}"
                    
                    print(f"检查iframe: {iframe_name}")
                    
                    content_frame = browser_tool._async_loop.run_until_complete(
                        iframe_handle.content_frame()
                    )
                    
                    if content_frame:
                        iframe_result = browser_tool._async_loop.run_until_complete(
                            content_frame.evaluate(extract_js)
                        )
                        
                        if iframe_result:
                            print(f"iframe '{iframe_name}' 提取结果: {json.dumps(iframe_result, ensure_ascii=False)}")
                            
                            # 检查是否有必要的数据
                            if iframe_result.get('position') != "未找到职位名称" or iframe_result.get('communicated_position'):
                                return iframe_result
                except Exception as e:
                    print(f"从iframe '{iframe_name}' 提取信息时出错: {str(e)}")
        
        # 如果没有找到任何数据，返回部分结果或默认值
        return main_result or {
            'position': "未找到职位名称",
            'communicated_position': "未找到沟通职位",
            'expectation_full': "未找到期望信息",
            'salary': "未找到薪资信息",
            'job_expectation': "未找到职位期望"
        }
        
    except Exception as e:
        print(f"提取职位信息时出错: {str(e)}")
        return {
            'position': "提取错误",
            'communicated_position': "提取错误",
            'expectation_full': "提取错误",
            'salary': "提取错误",
            'job_expectation': "提取错误",
            'error': str(e)
        }


def extract_position_info_by_selectors(browser_tool, page_index):
    """
    使用精确的CSS选择器提取职位信息，适用于已知结构的页面
    
    Args:
        browser_tool: 浏览器工具实例
        page_index: 页面索引
    
    Returns:
        dict: 包含职位、薪资和期望信息的字典
    """
    print("\n使用选择器精确提取职位信息...")
    
    # 获取页面
    page = browser_tool.context.pages[page_index]
    
    # 定义精确的提取JavaScript代码
    extract_specific_js = """
    () => {
        // 提取职位信息
        const positionData = {};
        
        // 职位名称 - 尝试多种选择器
        const positionNameSelectors = [
            'div[class*="position-item"] span[class*="position-name"]',
            'span[class*="position-name"]',
            '.position-content .position-item .value.high-light-boss span'
        ];
        
        for (const selector of positionNameSelectors) {
            const elem = document.querySelector(selector);
            if (elem) {
                positionData.position = elem.textContent.trim();
                break;
            }
        }
        
        // 期望职位和薪资
        const expectationSelectors = [
            'div[class*="position-item expect"] span[class*="value job"]',
            '.position-content .position-item.expect .value.job'
        ];
        
        for (const selector of expectationSelectors) {
            const elem = document.querySelector(selector);
            if (elem) {
                positionData.expectation_full = elem.textContent.trim();
                
                // 尝试提取薪资
                const salaryElem = elem.querySelector('i[class*="high-light-orange"]');
                if (salaryElem) {
                    positionData.salary = salaryElem.textContent.trim();
                    
                    // 尝试获取干净的职位期望文本（排除薪资部分）
                    let expectationText = positionData.expectation_full;
                    if (positionData.salary) {
                        expectationText = expectationText.replace(positionData.salary, '').trim();
                    }
                    positionData.job_expectation = expectationText;
                } else {
                    positionData.job_expectation = positionData.expectation_full;
                }
                break;
            }
        }
        
        // 尝试从DOM结构中获取更多信息
        const allPositionItems = document.querySelectorAll('div[class*="position-item"]');
        allPositionItems.forEach(item => {
            const labelElem = item.querySelector('span[class*="label"]');
            if (!labelElem) return;
            
            const label = labelElem.textContent.trim();
            const valueElem = item.querySelector('span[class*="value"]');
            if (!valueElem) return;
            
            const value = valueElem.textContent.trim();
            
            // 根据标签记录不同类型的信息
            if (label.includes('沟通职位')) {
                positionData.communicated_position = value;
                // 删除"更换职位"等后缀
                positionData.communicated_position = positionData.communicated_position.replace(/\s+更换职位$/, '').trim();
            } else if (label.includes('期望') && !positionData.expectation_full) {
                positionData.expectation_full = value;
                
                // 尝试查找薪资
                const salaryElem = valueElem.querySelector('i[class*="high-light-orange"]');
                if (salaryElem) {
                    positionData.salary = salaryElem.textContent.trim();
                }
            }
        });
        
        return positionData;
    }
    """
    
    try:
        # 在主页面执行提取
        main_result = browser_tool._async_loop.run_until_complete(
            page.evaluate(extract_specific_js)
        )
        
        if main_result:
            print(f"主页面精确提取结果: {json.dumps(main_result, ensure_ascii=False)}")
            
            # 检查是否有必要的数据
            if main_result.get('position') or main_result.get('communicated_position'):
                return main_result
        
        # 尝试在所有iframe中提取
        iframe_handles = browser_tool._async_loop.run_until_complete(
            page.query_selector_all('iframe')
        )
        
        if iframe_handles:
            print(f"发现 {len(iframe_handles)} 个iframe，尝试精确提取信息...")
            
            for i, iframe_handle in enumerate(iframe_handles):
                try:
                    iframe_name = browser_tool._async_loop.run_until_complete(
                        iframe_handle.get_attribute('name')
                    ) or f"iframe-{i}"
                    
                    print(f"检查iframe: {iframe_name}")
                    
                    content_frame = browser_tool._async_loop.run_until_complete(
                        iframe_handle.content_frame()
                    )
                    
                    if content_frame:
                        iframe_result = browser_tool._async_loop.run_until_complete(
                            content_frame.evaluate(extract_specific_js)
                        )
                        
                        if iframe_result:
                            print(f"iframe '{iframe_name}' 精确提取结果: {json.dumps(iframe_result, ensure_ascii=False)}")
                            
                            # 检查是否有必要的数据
                            if iframe_result.get('position') or iframe_result.get('communicated_position'):
                                return iframe_result
                except Exception as e:
                    print(f"从iframe '{iframe_name}' 精确提取信息时出错: {str(e)}")
        
        # 合并结果，确保有返回值
        return main_result or {
            'position': "未找到职位名称",
            'communicated_position': "未找到沟通职位",
            'expectation_full': "未找到期望信息",
            'salary': "未找到薪资信息",
            'job_expectation': "未找到职位期望"
        }
        
    except Exception as e:
        print(f"精确提取职位信息时出错: {str(e)}")
        return {
            'position': "提取错误",
            'communicated_position': "提取错误",
            'expectation_full': "提取错误",
            'salary': "提取错误",
            'job_expectation': "提取错误",
            'error': str(e)
        } 