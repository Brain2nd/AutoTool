#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
浏览器自动化工具模块

提供连接已打开浏览器的功能，支持对浏览器进行自动化操作
"""

import os
import json
import subprocess
import time
import sys
import pathlib
import asyncio
from typing import Dict, List, Any, Optional, Union

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext, Error as PlaywrightError
except ImportError:
    try:
        from playwright.async_api import async_playwright, Browser, Page, BrowserContext
        # 如果上面的导入成功但没有找到Error，使用Exception作为替代
        PlaywrightError = Exception
    except ImportError:
        print("请先安装playwright: pip install playwright pytest-playwright")
        print("然后安装浏览器驱动: playwright install")
        raise

# 添加项目根目录到Python路径
current_dir = pathlib.Path(__file__).parent
root_dir = current_dir.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# 导入RAGTool用于相似度计算
try:
    from ..rag.ragtool import RAGTool
except ImportError:
    print("警告: 未能导入RAGTool，相似度匹配功能将使用简化版算法")
    RAGTool = None


class BrowserTool:
    """浏览器自动化工具类，提供连接已有浏览器的功能"""
    
    def __init__(self, rag_config_name: str = "default"):
        """
        初始化浏览器工具
        
        Args:
            rag_config_name: RAG工具配置名称
        """
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._is_connected = False
        self._connection_info = {}
        self._async_loop = None
        self._saved_elements = {}  # 保存元素的字典
        self._element_cache_dir = pathlib.Path(current_dir / "elements_cache")  # 元素缓存目录
        
        # 确保元素缓存目录存在
        if not self._element_cache_dir.exists():
            self._element_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化RAG工具
        self.rag_tool = None
        if RAGTool is not None:
            try:
                self.rag_tool = RAGTool(rag_config_name)
                print("已成功初始化RAG工具")
            except Exception as e:
                print(f"初始化RAG工具时出错: {e}")
    
    def _sanitize_filename(self, name: str) -> str:
        """
        清理文件名，移除不合法字符
        
        Args:
            name: 原始名称
            
        Returns:
            清理后的合法文件名
        """
        # 替换不允许的字符
        invalid_chars = r'<>:"/\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # 限制长度
        if len(name) > 50:
            name = name[:47] + '...'
            
        return name.strip()
    
    def _get_auto_element_name(self, element: Dict[str, Any]) -> str:
        """
        基于元素属性自动生成元素名称
        
        Args:
            element: 元素信息字典
            
        Returns:
            生成的元素名称
        """
        # 优先使用元素文本内容
        if element.get('text') and element['text'].strip():
            name = element['text'].strip()
        # 其次使用元素类型和其他属性
        elif element.get('type'):
            type_name = element['type']
            # 对于链接或按钮，尝试使用其他属性丰富名称
            if type_name in ['link', 'button', 'tab', 'menuitem']:
                if element.get('title'):
                    name = f"{type_name}_{element['title']}"
                elif element.get('aria-label'):
                    name = f"{type_name}_{element['aria-label']}"
                elif element.get('ka'):
                    name = f"{type_name}_{element['ka']}"
                else:
                    # 如果没有有意义的属性，使用位置信息
                    rect = element.get('rect', {})
                    x = rect.get('x', 0)
                    y = rect.get('y', 0)
                    name = f"{type_name}_at_{x}_{y}"
            else:
                name = type_name
        else:
            # 如果没有类型信息，使用标签名和位置
            tag_name = element.get('tagName', 'element')
            rect = element.get('rect', {})
            x = rect.get('x', 0)
            y = rect.get('y', 0)
            name = f"{tag_name}_at_{x}_{y}"
        
        # 清理名称
        return self._sanitize_filename(name)
    
    def save_elements(self, elements: List[Dict[str, Any]], 
                    save_path: Optional[str] = None, 
                    prefix: str = "") -> Dict[str, Any]:
        """
        保存元素到文件
        
        Args:
            elements: 要保存的元素列表
            save_path: 保存路径，如果为None则使用默认路径
            prefix: 文件名前缀
            
        Returns:
            保存结果信息
        """
        result = {
            'success': False,
            'message': '',
            'saved_files': [],
            'element_names': []
        }
        
        try:
            # 确定保存路径
            if save_path:
                # 使用用户指定的路径，转换为绝对路径
                save_dir = pathlib.Path(save_path).absolute()
                if not save_dir.exists():
                    save_dir.mkdir(parents=True, exist_ok=True)
                    
                # 记录自定义目录到控制台，方便调试
                print(f"[DEBUG] 使用自定义保存目录: {save_dir}")
            else:
                # 使用默认路径
                save_dir = self._element_cache_dir
                print(f"[DEBUG] 使用默认缓存目录: {save_dir}")
            
            # 遍历元素并保存
            saved_files = []
            element_names = []
            
            for i, element in enumerate(elements):
                # 生成元素名称
                if prefix:
                    element_name = f"{prefix}_{i+1}"
                else:
                    element_name = self._get_auto_element_name(element)
                    # 确保名称唯一
                    counter = 1
                    base_name = element_name
                    while element_name in element_names:
                        element_name = f"{base_name}_{counter}"
                        counter += 1
                
                # 保存元素信息
                file_path = save_dir / f"{element_name}.json"
                
                # 确保目录存在
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(element, f, ensure_ascii=False, indent=2)
                
                # 打印保存成功信息，方便调试
                print(f"[DEBUG] 成功保存元素到: {file_path}")
                
                # 添加到结果
                saved_files.append(str(file_path))
                element_names.append(element_name)
                
                # 同时添加到内存中的缓存
                self._saved_elements[element_name] = element
            
            # 设置结果
            result['success'] = True
            result['message'] = f"成功保存 {len(saved_files)} 个元素"
            result['saved_files'] = saved_files
            result['element_names'] = element_names
            
            return result
        
        except Exception as e:
            import traceback
            print(f"[ERROR] 保存元素时出错: {str(e)}")
            print(traceback.format_exc())
            result['message'] = f"保存元素时出错: {str(e)}"
            return result
    
    def load_elements(self, path_or_names: Union[str, List[str]]) -> Dict[str, Any]:
        """
        加载保存的元素
        
        Args:
            path_or_names: 元素路径、目录或名称列表
            
        Returns:
            加载结果信息
        """
        result = {
            'success': False,
            'message': '',
            'elements': [],
            'element_names': []
        }
        
        try:
            loaded_elements = []
            element_names = []
            
            print(f"[DEBUG] 尝试加载元素: {path_or_names}")
            
            # 如果输入是字符串
            if isinstance(path_or_names, str):
                path_obj = pathlib.Path(path_or_names)
                
                # 先检查是否是绝对路径
                if path_obj.is_absolute():
                    print(f"[DEBUG] 检查绝对路径: {path_obj}")
                    # 如果是目录，加载目录中所有的.json文件
                    if path_obj.is_dir():
                        print(f"[DEBUG] 将从目录加载: {path_obj}")
                        for json_file in path_obj.glob('*.json'):
                            with open(json_file, 'r', encoding='utf-8') as f:
                                element = json.load(f)
                                loaded_elements.append(element)
                                element_names.append(json_file.stem)
                    
                    # 如果是单个文件，加载该文件
                    elif path_obj.is_file() and path_obj.suffix.lower() == '.json':
                        print(f"[DEBUG] 将从文件加载: {path_obj}")
                        with open(path_obj, 'r', encoding='utf-8') as f:
                            element = json.load(f)
                            loaded_elements.append(element)
                            element_names.append(path_obj.stem)
                
                # 如果是元素名称，从内存缓存中加载
                elif path_or_names in self._saved_elements:
                    print(f"[DEBUG] 从内存缓存加载: {path_or_names}")
                    loaded_elements.append(self._saved_elements[path_or_names])
                    element_names.append(path_or_names)
                
                # 尝试从默认目录加载
                else:
                    # 先尝试将相对路径转换为绝对路径
                    relative_path = pathlib.Path(path_or_names)
                    
                    # 尝试作为目录
                    if relative_path.exists() and relative_path.is_dir():
                        print(f"[DEBUG] 尝试作为相对目录: {relative_path}")
                        for json_file in relative_path.glob('*.json'):
                            with open(json_file, 'r', encoding='utf-8') as f:
                                element = json.load(f)
                                loaded_elements.append(element)
                                element_names.append(json_file.stem)
                    
                    # 尝试作为文件
                    elif relative_path.exists() and relative_path.is_file() and relative_path.suffix.lower() == '.json':
                        print(f"[DEBUG] 尝试作为相对文件: {relative_path}")
                        with open(relative_path, 'r', encoding='utf-8') as f:
                            element = json.load(f)
                            loaded_elements.append(element)
                            element_names.append(relative_path.stem)
                    
                    # 尝试从默认元素缓存目录加载
                    else:
                        default_path = self._element_cache_dir / f"{path_or_names}.json"
                        print(f"[DEBUG] 尝试从默认目录加载: {default_path}")
                        if default_path.exists():
                            with open(default_path, 'r', encoding='utf-8') as f:
                                element = json.load(f)
                                loaded_elements.append(element)
                                element_names.append(path_or_names)
                        else:
                            print(f"[DEBUG] 在默认目录中找不到元素: {path_or_names}")
                            
                            # 查找其他可能的目录
                            # 检查当前工作目录
                            cwd_path = pathlib.Path.cwd() / f"{path_or_names}.json"
                            if cwd_path.exists():
                                print(f"[DEBUG] 在当前工作目录找到: {cwd_path}")
                                with open(cwd_path, 'r', encoding='utf-8') as f:
                                    element = json.load(f)
                                    loaded_elements.append(element)
                                    element_names.append(path_or_names)
                            else:
                                # 尝试搜索所有已知的元素目录
                                for search_dir in [self._element_cache_dir, pathlib.Path.cwd()]:
                                    for json_file in search_dir.glob('**/*.json'):
                                        if json_file.stem == path_or_names:
                                            print(f"[DEBUG] 找到匹配的文件: {json_file}")
                                            with open(json_file, 'r', encoding='utf-8') as f:
                                                element = json.load(f)
                                                loaded_elements.append(element)
                                                element_names.append(path_or_names)
                                                break
                                
                                if not loaded_elements:
                                    result['message'] = f"找不到元素: {path_or_names}"
                                    return result
            
            # 如果输入是列表
            elif isinstance(path_or_names, list):
                for name in path_or_names:
                    # 从内存缓存加载
                    if name in self._saved_elements:
                        print(f"[DEBUG] 从内存缓存加载列表项: {name}")
                        loaded_elements.append(self._saved_elements[name])
                        element_names.append(name)
                    else:
                        # 尝试从默认目录加载
                        default_path = self._element_cache_dir / f"{name}.json"
                        print(f"[DEBUG] 尝试从默认目录加载列表项: {default_path}")
                        if default_path.exists():
                            with open(default_path, 'r', encoding='utf-8') as f:
                                element = json.load(f)
                                loaded_elements.append(element)
                                element_names.append(name)
                        else:
                            print(f"[DEBUG] 在默认目录中找不到列表项: {name}")
                            # 尝试作为完整路径
                            path_obj = pathlib.Path(name)
                            if path_obj.exists() and path_obj.is_file() and path_obj.suffix.lower() == '.json':
                                print(f"[DEBUG] 作为完整路径加载列表项: {path_obj}")
                                with open(path_obj, 'r', encoding='utf-8') as f:
                                    element = json.load(f)
                                    loaded_elements.append(element)
                                    element_names.append(path_obj.stem)
            
            # 设置结果
            if loaded_elements:
                result['success'] = True
                result['message'] = f"成功加载 {len(loaded_elements)} 个元素"
                result['elements'] = loaded_elements
                result['element_names'] = element_names
            else:
                result['message'] = "未找到任何元素"
            
            return result
        
        except Exception as e:
            import traceback
            print(f"[ERROR] 加载元素时出错: {str(e)}")
            print(traceback.format_exc())
            result['message'] = f"加载元素时出错: {str(e)}"
            return result
    
    def list_saved_elements(self, directory: Optional[str] = None) -> Dict[str, Any]:
        """
        列出已保存的元素
        
        Args:
            directory: 要列出元素的目录，如果为None则使用默认路径
            
        Returns:
            保存的元素列表
        """
        result = {
            'success': False,
            'message': '',
            'elements': []
        }
        
        try:
            # 确定目录
            search_dirs = []
            
            if directory:
                # 尝试使用用户指定的路径
                dir_path = pathlib.Path(directory)
                if dir_path.exists() and dir_path.is_dir():
                    search_dirs.append(dir_path)
                    print(f"[DEBUG] 将搜索指定目录: {dir_path}")
                else:
                    # 尝试从项目根目录解析相对路径
                    root_relative = pathlib.Path(root_dir) / directory
                    if root_relative.exists() and root_relative.is_dir():
                        search_dirs.append(root_relative)
                        print(f"[DEBUG] 将搜索项目根目录相对路径: {root_relative}")
            
            # 始终包含默认缓存目录
            if not directory or not search_dirs:
                search_dirs.append(self._element_cache_dir)
                print(f"[DEBUG] 将搜索默认缓存目录: {self._element_cache_dir}")
            
            # 包含最近使用的自定义目录
            for path in search_dirs:
                print(f"[DEBUG] 搜索目录: {path}")
            
            # 收集所有元素
            element_info = []
            
            # 搜索内存缓存
            print(f"[DEBUG] 内存中有 {len(self._saved_elements)} 个缓存元素")
            
            for name, element in self._saved_elements.items():
                info = {
                    'name': name,
                    'file_path': "内存缓存",
                    'type': element.get('type', 'unknown'),
                    'text': element.get('text', ''),
                    'selector': element.get('cssSelector', '')
                }
                element_info.append(info)
            
            # 搜索文件系统
            for dir_path in search_dirs:
                if not dir_path.exists():
                    print(f"[DEBUG] 目录不存在: {dir_path}")
                    continue
                
                # 递归搜索所有json文件
                element_files = list(dir_path.glob('**/*.json'))
                print(f"[DEBUG] 在 {dir_path} 中找到 {len(element_files)} 个JSON文件")
                
                for file_path in element_files:
                    try:
                        # 读取元素信息
                        with open(file_path, 'r', encoding='utf-8') as f:
                            element = json.load(f)
                        
                        # 检查这是否是一个元素文件(通过检查关键字段)
                        if 'type' in element and 'cssSelector' in element:
                            # 提取关键信息
                            info = {
                                'name': file_path.stem,
                                'file_path': str(file_path),
                                'type': element.get('type', 'unknown'),
                                'text': element.get('text', ''),
                                'selector': element.get('cssSelector', '')
                            }
                            
                            # 检查是否已存在同名元素(内存中的优先)
                            if not any(e['name'] == info['name'] for e in element_info):
                                element_info.append(info)
                    except Exception as e:
                        print(f"[DEBUG] 读取元素文件 {file_path} 时出错: {e}")
            
            # 设置结果
            result['success'] = True
            result['message'] = f"找到 {len(element_info)} 个已保存的元素"
            result['elements'] = element_info
            
            return result
        
        except Exception as e:
            import traceback
            print(f"[ERROR] 列出元素时出错: {str(e)}")
            print(traceback.format_exc())
            result['message'] = f"列出元素时出错: {str(e)}"
            return result
    
    def find_and_save_elements(self, page_index: int, description: str, 
                            similarity_threshold: float = 0.3,
                            save_path: Optional[str] = None,
                            prefix: str = "",
                            max_results: int = 5,
                            include_iframes: bool = True) -> Dict[str, Any]:
        """
        查找并保存符合描述的元素
        
        Args:
            page_index: 页面序号（从0开始）
            description: 功能描述文本
            similarity_threshold: 相似度阈值，默认0.3
            save_path: 保存路径，如果为None则使用默认路径
            prefix: 文件名前缀
            max_results: 最大保存结果数
            include_iframes: 是否在iframe中查找元素
            
        Returns:
            查找和保存结果
        """
        result = {
            'success': False,
            'message': '',
            'matches': [],
            'saved_elements': [],
            'element_names': [],
            'save_path': None,  # 添加保存路径信息
            'iframe_elements': 0  # 添加来自iframe的元素数量
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        try:
            # 处理保存路径
            if save_path:
                # 将相对路径转换为绝对路径
                abs_save_path = pathlib.Path(save_path).absolute()
                print(f"[DEBUG] 使用指定保存路径: {abs_save_path}")
                
                # 确保目录存在
                if not abs_save_path.exists():
                    print(f"[DEBUG] 创建目录: {abs_save_path}")
                    abs_save_path.mkdir(parents=True, exist_ok=True)
                    
                # 更新保存路径
                save_path = str(abs_save_path)
                result['save_path'] = save_path
            else:
                # 使用默认缓存目录
                result['save_path'] = str(self._element_cache_dir)
                
            # 首先查找匹配的元素 - 使用增强的相似度搜索，支持iframe
            print(f"[DEBUG] 搜索匹配 '{description}' 的元素...")
            search_result = self.find_elements_by_similarity(
                page_index, 
                description, 
                None,  # 默认使用所有元素类型 
                similarity_threshold, 
                max_results,
                include_iframes  # 包含iframe元素
            )
            
            if not search_result['success']:
                result['message'] = search_result['message']
                return result
            
            # 获取匹配元素
            matches = search_result.get('elements', [])
            
            if not matches:
                result['message'] = f"未找到与 '{description}' 相似的元素"
                return result
            
            # 计算iframe中的元素数量
            iframe_elements = sum(1 for element in matches if element.get('from_iframe', False))
            result['iframe_elements'] = iframe_elements
            
            if iframe_elements > 0:
                print(f"[DEBUG] 找到 {iframe_elements} 个来自iframe的元素")
            
            # 限制保存数量
            if max_results > 0 and len(matches) > max_results:
                matches = matches[:max_results]
            
            # 保存元素
            print(f"[DEBUG] 开始保存 {len(matches)} 个元素...")
            save_result = self.save_elements(matches, save_path, prefix)
            
            if not save_result['success']:
                result['message'] = save_result['message']
                return result
            
            # 设置结果
            result['success'] = True
            result['message'] = f"成功找到并保存了 {len(matches)} 个与 '{description}' 相似的元素"
            if iframe_elements > 0:
                result['message'] += f"（其中 {iframe_elements} 个来自iframe）"
            
            result['matches'] = matches
            result['saved_elements'] = save_result['saved_files']
            result['element_names'] = save_result['element_names']
            
            # 打印保存路径信息
            print(f"[DEBUG] 元素已保存到: {result['save_path']}")
            print(f"[DEBUG] 元素名称: {result['element_names']}")
            
            return result
            
        except Exception as e:
            import traceback
            print(f"[ERROR] 查找并保存元素时出错: {str(e)}")
            print(traceback.format_exc())
            result['message'] = f"查找并保存元素时出错: {str(e)}"
            return result
    
    def click_saved_element(self, element_name: str, page_index: int,
                         click_type: str = 'click', 
                         wait_for_navigation: bool = True) -> Dict[str, Any]:
        """
        点击已保存的元素
        
        Args:
            element_name: 元素名称或文件路径
            page_index: 页面序号（从0开始）
            click_type: 点击类型 (click, dblclick, hover)
            wait_for_navigation: 是否等待页面导航完成
            
        Returns:
            点击操作结果
        """
        result = {
            'success': False,
            'message': '',
            'title': None,
            'url': None
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        try:
            # 加载元素
            load_result = self.load_elements(element_name)
            
            if not load_result['success']:
                result['message'] = load_result['message']
                return result
            
            if not load_result['elements']:
                result['message'] = f"未找到元素: {element_name}"
                return result
            
            # 获取元素信息
            element = load_result['elements'][0]  # 使用第一个匹配的元素
            
            # 获取元素选择器
            selector = element.get('cssSelector')
            
            if not selector:
                # 如果没有CSS选择器，尝试使用XPath
                selector = element.get('xpath')
                
            if not selector:
                result['message'] = f"元素 '{element_name}' 没有有效的选择器"
                return result
            
            # 点击元素
            click_result = self.click_element(
                page_index=page_index,
                element_selector=selector,
                click_type=click_type,
                wait_for_navigation=wait_for_navigation
            )
            
            # 返回点击结果
            return click_result
            
        except Exception as e:
            result['message'] = f"点击元素时出错: {str(e)}"
            return result
    
    async def _connect_to_browser_async(self, browser_type: str = 'chromium', 
                                      endpoint_url: Optional[str] = None, 
                                      timeout: int = 30000,
                                      preferred_port: Optional[int] = None) -> Dict[str, Any]:
        """
        异步连接到已打开的浏览器
        
        Args:
            browser_type: 浏览器类型，支持 'chromium', 'firefox', 'webkit'
            endpoint_url: CDP 终端URL，如果为None则尝试查找已打开的浏览器
            timeout: 连接超时时间(毫秒)
            
        Returns:
            连接结果信息
        """
        result = {
            'success': False,
            'message': '',
            'pages': [],
            'current_page_title': None,
            'current_page_url': None
        }
        
        try:
            # 启动playwright
            self.playwright = await async_playwright().start()
            
            # 如果没有提供endpoint_url，则尝试获取已打开Chrome的调试地址
            if not endpoint_url and browser_type == 'chromium':
                # 查找已运行的Chrome调试端口
                try:
                    # Windows系统查找Chrome进程
                    if sys.platform == 'win32':
                        chrome_process = subprocess.run(
                            ['powershell', '-Command', 'Get-Process | Where-Object {$_.Name -like "*chrome*" -and $_.MainWindowTitle -ne ""} | Select-Object Id'],
                            capture_output=True, text=True
                        )
                        if chrome_process.returncode == 0:
                            # 从输出中提取进程ID
                            lines = chrome_process.stdout.strip().split('\n')
                            pid = None
                            for line in lines:
                                if line.strip().isdigit():
                                    pid = line.strip()
                                    break
                            
                            if pid:
                                # 检查是否在调试模式
                                json_url = f"http://localhost:9222/json"
                                try:
                                    import requests
                                    response = requests.get(json_url, timeout=2)
                                    if response.status_code == 200:
                                        endpoint_url = "http://localhost:9222"
                                    else:
                                        result['message'] = "Chrome未在调试模式下运行，请使用--remote-debugging-port=9222启动Chrome"
                                        return result
                                except:
                                    result['message'] = "无法连接到Chrome调试端口，请确保已使用--remote-debugging-port=9222启动Chrome"
                                    return result
                        else:
                            result['message'] = "未找到正在运行的Chrome浏览器"
                            return result
                    # Linux/Mac系统查找Chrome进程
                    else:
                        # 如果指定了preferred_port，只尝试连接该端口
                        if preferred_port:
                            debug_ports = [preferred_port]
                            print(f"🎯 强制使用指定端口: {preferred_port}")
                        else:
                            # 智能端口检测：根据调用脚本路径和当前工作目录优先选择对应端口
                            import os
                            import inspect
                            
                            current_dir = os.getcwd()
                            
                            # 获取调用栈信息，找出是哪个task脚本在调用
                            calling_script = ""
                            try:
                                # 检查调用栈中的脚本路径
                                for frame_info in inspect.stack():
                                    filename = frame_info.filename
                                    if any(task in filename for task in ['influencertool', 'hr', 'larkbusiness', 'sca']):
                                        calling_script = filename
                                        break
                                
                                # 如果调用栈中没找到，检查主脚本参数
                                if not calling_script and len(sys.argv) > 0:
                                    calling_script = sys.argv[0]
                            except:
                                calling_script = ""
                            
                            # 根据调用脚本路径和当前目录确定优先端口顺序
                            if 'influencertool' in calling_script or 'influencertool' in current_dir:
                                debug_ports = [9223, 9222, 9224, 9225]  # influencertool优先
                            elif 'hr' in calling_script or 'hr' in current_dir:
                                debug_ports = [9224, 9222, 9223, 9225]  # hr优先
                            elif 'larkbusiness' in calling_script or 'larkbusiness' in current_dir:
                                debug_ports = [9222, 9223, 9224, 9225]  # larkbusiness优先
                            elif 'sca' in calling_script or 'sca' in current_dir:
                                debug_ports = [9225, 9222, 9223, 9224]  # sca优先
                            else:
                                debug_ports = [9222, 9223, 9224, 9225]  # 默认顺序
                            
                            print(f"🔍 智能端口检测 - 当前目录: {current_dir}")
                            print(f"🔍 调用脚本路径: {calling_script}")
                            print(f"🎯 端口检测顺序: {debug_ports}")
                        
                        for port in debug_ports:
                            try:
                                import requests
                                json_url = f"http://localhost:{port}/json"
                                response = requests.get(json_url, timeout=2)
                                if response.status_code == 200:
                                    endpoint_url = f"http://localhost:{port}"
                                    print(f"✅ 成功连接到端口 {port}")
                                    break
                                else:
                                    print(f"❌ 端口 {port} 响应异常: HTTP {response.status_code}")
                            except:
                                if preferred_port:
                                    # 如果是指定端口失败，给出明确的错误信息
                                    print(f"❌ 无法连接到指定端口 {port}")
                                continue
                        
                        if not endpoint_url:
                            result['message'] = "未找到正在运行的Chrome调试端口，请使用--remote-debugging-port=9222启动Chrome"
                            return result
                except Exception as e:
                    result['message'] = f"查找Chrome进程失败: {str(e)}"
                    return result
            
            # 如果仍未获取到endpoint_url，报错
            if not endpoint_url:
                result['message'] = "未提供浏览器调试地址，也无法自动查找"
                return result
                
            # 根据浏览器类型获取相应的浏览器对象
            browser_instance = getattr(self.playwright, browser_type)
            
            # 连接到浏览器
            self.browser = await browser_instance.connect_over_cdp(
                endpoint_url=endpoint_url,
                timeout=timeout
            )
            
            # 获取默认上下文
            self.context = self.browser.contexts[0] if self.browser.contexts else None
            
            if not self.context:
                result['message'] = "浏览器连接成功但无法获取上下文"
                return result
            
            # 获取所有页面
            pages = self.context.pages
            
            if not pages:
                result['message'] = "浏览器连接成功但没有打开的页面"
                return result
            
            # 使用当前活动页面
            self.page = pages[0]  # 默认使用第一个页面
            
            # 获取页面信息
            page_infos = []
            for i, p in enumerate(pages):
                title = await p.title()
                url = p.url
                page_infos.append({
                    'index': i,
                    'title': title,
                    'url': url
                })
            
            # 设置连接标志
            self._is_connected = True
            self._connection_info = {
                'browser_type': browser_type,
                'endpoint_url': endpoint_url,
                'pages_count': len(pages)
            }
            
            # 设置结果
            result['success'] = True
            result['message'] = f"成功连接到{browser_type}浏览器"
            result['pages'] = page_infos
            
            # 获取当前页面信息
            current_title = await self.page.title()
            current_url = self.page.url
            
            result['current_page_title'] = current_title
            result['current_page_url'] = current_url
            
            return result
            
        except PlaywrightError as e:
            if "Target closed" in str(e) or "Connection closed" in str(e):
                result['message'] = "浏览器连接已关闭，可能是浏览器被关闭了"
            else:
                result['message'] = f"Playwright错误: {str(e)}"
            await self._cleanup()
            return result
            
        except Exception as e:
            result['message'] = f"连接浏览器时出错: {str(e)}"
            await self._cleanup()
            return result
    
    def connect_to_browser(self, browser_type: str = 'chromium', 
                         endpoint_url: Optional[str] = None,
                         timeout: int = 30000,
                         preferred_port: Optional[int] = None) -> Dict[str, Any]:
        """
        连接到已打开的浏览器
        
        Args:
            browser_type: 浏览器类型，支持 'chromium', 'firefox', 'webkit'
            endpoint_url: CDP 终端URL，如果为None则尝试查找已打开的浏览器
            timeout: 连接超时时间(毫秒)
            
        Returns:
            连接结果信息
        """
        # 创建新的事件循环
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        # 执行异步方法
        try:
            return self._async_loop.run_until_complete(
                self._connect_to_browser_async(browser_type, endpoint_url, timeout, preferred_port)
            )
        except Exception as e:
            return {
                'success': False,
                'message': f"执行异步连接时出错: {str(e)}"
            }
    
    async def _cleanup(self):
        """清理资源"""
        if self.browser:
            try:
                await self.browser.close()
            except:
                pass
            self.browser = None
        
        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass
            self.playwright = None
        
        self.context = None
        self.page = None
        self._is_connected = False
    
    def disconnect(self) -> Dict[str, Any]:
        """
        断开与浏览器的连接
        
        Returns:
            断开连接的结果信息
        """
        if not self._is_connected:
            return {
                'success': True,
                'message': "浏览器已经断开连接"
            }
        
        try:
            # 优先尝试异步清理
            if self._async_loop:
                try:
                    # 检查事件循环是否仍然有效
                    if not self._async_loop.is_closed():
                        self._async_loop.run_until_complete(self._cleanup())
                        return {
                            'success': True,
                            'message': "已断开与浏览器的连接 (异步清理)"
                        }
                    else:
                        # 事件循环已关闭，使用同步清理
                        self._cleanup_sync()
                        return {
                            'success': True,
                            'message': "已断开与浏览器的连接 (同步清理)"
                        }
                except Exception as async_e:
                    # 异步清理失败，回退到同步清理
                    print(f"⚠️ 异步清理失败，使用同步清理: {async_e}")
                    self._cleanup_sync()
                    return {
                        'success': True,
                        'message': "已断开与浏览器的连接 (回退到同步清理)"
                    }
            else:
                # 没有事件循环，直接使用同步清理
                self._cleanup_sync()
                return {
                    'success': True,
                    'message': "已断开与浏览器的连接 (直接同步清理)"
                }
                
        except Exception as e:
            # 最后的保险，确保至少标记为已断开
            self._is_connected = False
            return {
                'success': False,
                'message': f"断开连接时出错，但已标记为断开: {str(e)}"
            }
    
    def is_connected(self) -> bool:
        """
        检查是否已连接到浏览器
        
        Returns:
            是否已连接
        """
        return self._is_connected
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        获取连接信息
        
        Returns:
            连接信息字典
        """
        if not self._is_connected:
            return {
                'is_connected': False,
                'message': "未连接到浏览器"
            }
        
        info = {
            'is_connected': True,
            **self._connection_info
        }
        
        # 添加额外信息
        return info
    
    async def _switch_to_page_async(self, page_index: int) -> Dict[str, Any]:
        """
        异步切换到指定序号的页面
        
        Args:
            page_index: 页面序号（从0开始）
            
        Returns:
            切换结果信息
        """
        result = {
            'success': False,
            'message': '',
            'title': None,
            'url': None
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        if not self.context:
            result['message'] = "无法获取浏览器上下文"
            return result
            
        # 获取所有页面
        pages = self.context.pages
        
        # 检查页面序号是否有效
        if page_index < 0 or page_index >= len(pages):
            result['message'] = f"无效的页面序号: {page_index}，有效范围: 0-{len(pages)-1}"
            return result
        
        try:
            # 切换到指定页面
            self.page = pages[page_index]
            
            # 使页面成为焦点
            await self.page.bring_to_front()
            
            # 获取页面信息
            title = await self.page.title()
            url = self.page.url
            
            # 设置结果
            result['success'] = True
            result['message'] = f"成功切换到页面: {title}"
            result['title'] = title
            result['url'] = url
            
            return result
            
        except PlaywrightError as e:
            result['message'] = f"切换页面时出错: {str(e)}"
            return result
            
        except Exception as e:
            result['message'] = f"切换页面时发生异常: {str(e)}"
            return result
    
    def switch_to_page(self, page_index: int) -> Dict[str, Any]:
        """
        切换到指定序号的页面
        
        Args:
            page_index: 页面序号（从0开始）
            
        Returns:
            切换结果信息
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': "未连接到浏览器，请先连接"
            }
        
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        try:
            return self._async_loop.run_until_complete(
                self._switch_to_page_async(page_index)
            )
        except Exception as e:
            return {
                'success': False,
                'message': f"执行页面切换时出错: {str(e)}"
            }
    
    async def _navigate_async(self, url: str) -> Dict[str, Any]:
        """
        异步导航到指定URL
        
        Args:
            url: 要导航到的URL
            
        Returns:
            导航结果信息
        """
        result = {
            'success': False,
            'message': '',
            'title': None,
            'url': None
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        if not self.page:
            result['message'] = "无法获取当前页面"
            return result
        
        try:
            # 导航到指定URL
            response = await self.page.goto(url, wait_until='domcontentloaded')
            
            # 等待页面加载
            await self.page.wait_for_load_state('networkidle')
            
            # 获取页面信息
            title = await self.page.title()
            current_url = self.page.url
            
            # 设置结果
            result['success'] = True
            result['message'] = f"成功导航到: {title}"
            result['title'] = title
            result['url'] = current_url
            result['status'] = response.status if response else None
            
            return result
            
        except PlaywrightError as e:
            result['message'] = f"导航时出错: {str(e)}"
            return result
            
        except Exception as e:
            result['message'] = f"导航时发生异常: {str(e)}"
            return result
    
    def navigate(self, url: str) -> Dict[str, Any]:
        """
        在当前页面导航到指定URL
        
        Args:
            url: 要导航到的URL
            
        Returns:
            导航结果信息
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': "未连接到浏览器，请先连接"
            }
        
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        try:
            return self._async_loop.run_until_complete(
                self._navigate_async(url)
            )
        except Exception as e:
            return {
                'success': False,
                'message': f"执行页面导航时出错: {str(e)}"
            }
    
    async def _create_new_tab_async(self, url: str = 'about:blank') -> Dict[str, Any]:
        """
        异步创建新的标签页
        
        Args:
            url: 新标签页的URL，默认为空白页
            
        Returns:
            创建结果信息
        """
        result = {
            'success': False,
            'message': '',
            'page_index': -1,
            'title': None,
            'url': None
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        if not self.context:
            result['message'] = "无法获取浏览器上下文"
            return result
        
        try:
            # 创建新的页面
            new_page = await self.context.new_page()
            
            # 导航到指定URL
            await new_page.goto(url, wait_until='domcontentloaded')
            
            # 等待页面加载
            await new_page.wait_for_load_state('networkidle')
            
            # 获取页面信息
            title = await new_page.title()
            current_url = new_page.url
            
            # 获取页面序号
            pages = self.context.pages
            page_index = next((i for i, p in enumerate(pages) if p == new_page), -1)
            
            # 切换到新页面
            self.page = new_page
            
            # 设置结果
            result['success'] = True
            result['message'] = f"成功创建新标签页: {title}"
            result['page_index'] = page_index
            result['title'] = title
            result['url'] = current_url
            
            return result
            
        except PlaywrightError as e:
            result['message'] = f"创建新标签页时出错: {str(e)}"
            return result
            
        except Exception as e:
            result['message'] = f"创建新标签页时发生异常: {str(e)}"
            return result
    
    def create_new_tab(self, url: str = 'about:blank') -> Dict[str, Any]:
        """
        创建新的标签页
        
        Args:
            url: 新标签页的URL，默认为空白页
            
        Returns:
            创建结果信息
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': "未连接到浏览器，请先连接"
            }
        
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        try:
            return self._async_loop.run_until_complete(
                self._create_new_tab_async(url)
            )
        except Exception as e:
            return {
                'success': False,
                'message': f"执行创建新标签页时出错: {str(e)}"
            }
    
    async def _create_new_tab_background_async(self, url: str = 'about:blank') -> Dict[str, Any]:
        """
        异步在后台创建新的标签页（不切换焦点）
        
        Args:
            url: 新标签页的URL，默认为空白页
            
        Returns:
            创建结果信息
        """
        result = {
            'success': False,
            'message': '',
            'page_index': -1,
            'title': None,
            'url': None
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        if not self.context:
            result['message'] = "无法获取浏览器上下文"
            return result
        
        try:
            # 保存当前页面引用
            current_page = self.page
            
            # 创建新的页面
            new_page = await self.context.new_page()
            
            # 导航到指定URL
            await new_page.goto(url, wait_until='domcontentloaded')
            
            # 等待页面加载
            await new_page.wait_for_load_state('networkidle')
            
            # 获取页面信息
            title = await new_page.title()
            current_url = new_page.url
            
            # 获取页面序号
            pages = self.context.pages
            page_index = next((i for i, p in enumerate(pages) if p == new_page), -1)
            
            # 重要：不切换到新页面，保持原页面的焦点
            # self.page = new_page  # 注释掉这行
            
            # 如果有原页面，将焦点切回原页面
            if current_page and not current_page.is_closed():
                await current_page.bring_to_front()
            
            # 设置结果
            result['success'] = True
            result['message'] = f"成功在后台创建新标签页: {title}"
            result['page_index'] = page_index
            result['title'] = title
            result['url'] = current_url
            
            return result
            
        except PlaywrightError as e:
            result['message'] = f"创建新标签页时出错: {str(e)}"
            return result
            
        except Exception as e:
            result['message'] = f"创建新标签页时发生异常: {str(e)}"
            return result
    
    async def _navigate_page_async(self, page_index: int, url: str) -> Dict[str, Any]:
        """
        异步让指定序号的页面导航到URL
        
        Args:
            page_index: 页面序号（从0开始）
            url: 要导航到的URL
            
        Returns:
            导航结果信息
        """
        result = {
            'success': False,
            'message': '',
            'title': None,
            'url': None,
            'status': None
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        if not self.context:
            result['message'] = "无法获取浏览器上下文"
            return result
            
        # 获取所有页面
        pages = self.context.pages
        
        # 检查页面序号是否有效
        if page_index < 0 or page_index >= len(pages):
            result['message'] = f"无效的页面序号: {page_index}，有效范围: 0-{len(pages)-1}"
            return result
        
        try:
            # 获取指定序号的页面
            target_page = pages[page_index]
            
            # 导航到指定URL
            response = await target_page.goto(url, wait_until='domcontentloaded')
            
            # 等待页面加载
            await target_page.wait_for_load_state('networkidle')
            
            # 获取页面信息
            title = await target_page.title()
            current_url = target_page.url
            
            # 设置结果
            result['success'] = True
            result['message'] = f"成功将页面 {page_index} 导航到: {title}"
            result['title'] = title
            result['url'] = current_url
            result['status'] = response.status if response else None
            
            return result
            
        except PlaywrightError as e:
            result['message'] = f"导航页面 {page_index} 时出错: {str(e)}"
            return result
            
        except Exception as e:
            result['message'] = f"导航页面 {page_index} 时发生异常: {str(e)}"
            return result
    
    def navigate_page(self, page_index: int, url: str) -> Dict[str, Any]:
        """
        导航指定页面到URL
        
        Args:
            page_index: 页面索引
            url: 目标URL
            
        Returns:
            操作结果
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': '浏览器未连接'
            }
        
        # 创建新的事件循环来运行异步操作
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(self._navigate_page_async(page_index, url))
            return result
        finally:
            loop.close()
    
    async def _refresh_page_async(self, page_index: int, wait_until: str = 'networkidle') -> Dict[str, Any]:
        """
        异步刷新指定页面并等待加载完成
        
        Args:
            page_index: 页面索引
            wait_until: 等待条件
            
        Returns:
            操作结果
        """
        result = {
            'success': False,
            'message': '',
            'page_title': '',
            'page_url': '',
            'load_time': 0
        }
        
        try:
            # 获取所有页面
            pages = self.context.pages
            
            # 检查页面索引是否有效
            if page_index < 0 or page_index >= len(pages):
                result['message'] = f'无效的页面索引: {page_index}，当前有 {len(pages)} 个页面'
                return result
            
            # 获取目标页面
            target_page = pages[page_index]
            
            # 记录开始时间
            start_time = time.time()
            
            # 添加重试机制
            max_retries = 3
            retry_delay = 5  # 秒
            
            for attempt in range(max_retries):
                try:
                    # 刷新页面并等待加载完成
                    await target_page.reload(wait_until=wait_until, timeout=30000)
                    
                    # 等待一小段时间确保页面稳定
                    await asyncio.sleep(0.5)
                    
                    # 如果成功，跳出重试循环
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    if 'ERR_CONNECTION_RESET' in error_msg or 'net::ERR_CONNECTION_RESET' in error_msg:
                        if attempt < max_retries - 1:
                            print(f"[警告] 页面刷新遇到连接重置错误，{retry_delay}秒后重试 (尝试 {attempt + 1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            result['message'] = f'页面刷新失败: 连接被重置，已重试{max_retries}次'
                            return result
                    else:
                        # 其他错误直接抛出
                        raise
            
            # 计算加载时间
            load_time = time.time() - start_time
            
            # 获取页面信息
            page_title = await target_page.title()
            page_url = target_page.url
            
            result['success'] = True
            result['message'] = f'成功刷新页面: {page_title}'
            result['page_title'] = page_title
            result['page_url'] = page_url
            result['load_time'] = round(load_time, 2)
            
            return result
            
        except asyncio.TimeoutError:
            result['message'] = '页面刷新超时（30秒）'
            return result
        except Exception as e:
            result['message'] = f'刷新页面时出错: {str(e)}'
            return result
    
    def refresh_page(self, page_index: int, wait_until: str = 'networkidle') -> Dict[str, Any]:
        """
        刷新指定页面并等待加载完成
        
        Args:
            page_index: 页面索引
            wait_until: 等待条件，可选值：
                - 'load': 等待load事件触发
                - 'domcontentloaded': 等待DOMContentLoaded事件
                - 'networkidle': 等待网络空闲（推荐，等待页面完全加载）
                - 'commit': 等待页面开始加载
            
        Returns:
            操作结果，包含：
                - success: 是否成功
                - message: 结果消息
                - page_title: 页面标题
                - page_url: 页面URL
                - load_time: 加载时间（秒）
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': '浏览器未连接'
            }
        
        # 使用已存在的事件循环，如果没有则创建一个
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        try:
            result = self._async_loop.run_until_complete(self._refresh_page_async(page_index, wait_until))
            return result
        except Exception as e:
            return {
                'success': False,
                'message': f'刷新页面时出错: {str(e)}'
            }
    
    async def _get_page_dom_async(self, page_index: int, selector: str = 'html') -> Dict[str, Any]:
        """
        异步获取指定页面的DOM结构，优化版本
        
        Args:
            page_index: 页面序号（从0开始）
            selector: CSS选择器，默认为'html'（整个页面）
            
        Returns:
            包含DOM结构的结果信息
        """
        result = {
            'success': False,
            'message': '',
            'title': None,
            'url': None,
            'dom': None,
            'selector': selector,
            'has_iframes': False,
            'iframe_count': 0
        }
        
        # 确保浏览器已连接
        if not self._is_connected or not self.context:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        # 安全获取页面
        try:
            pages = self.context.pages
            if not pages or page_index < 0 or page_index >= len(pages):
                result['message'] = f"无效的页面序号: {page_index}，有效范围: 0-{len(pages)-1 if pages else 0}"
                return result
            
            target_page = pages[page_index]
            if target_page.is_closed():
                result['message'] = f"页面 {page_index} 已关闭"
                return result
        except Exception as e:
            result['message'] = f"获取页面时出错: {str(e)}"
            return result
        
        # 主要DOM获取逻辑
        try:
            # 1. 获取基本页面信息
            try:
                title = await target_page.title()
                current_url = target_page.url
                result['title'] = title
                result['url'] = current_url
            except Exception as e:
                print(f"[警告] 获取页面信息时出错: {str(e)}")
                # 继续执行，不中断流程
            
            # 2. 确定获取方式：全页面或特定元素
            if selector and selector != 'html':
                # 获取特定元素
                dom = await self._get_element_html(target_page, selector)
            else:
                # 获取全页面（包括iframe内容）
                dom = await self._get_full_page_html(target_page, include_iframes=True)
                
            if not dom:
                result['message'] = "无法获取DOM内容"
                return result
                
            # 3. 处理返回结果
            # 检查是否为增强的DOM结构（包含iframe信息）
            if isinstance(dom, dict) and 'main_html' in dom:
                # 含有iframe的增强结构
                result['has_iframes'] = True
                result['iframe_count'] = dom.get('iframe_count', 0)
                result['iframes'] = dom.get('iframes', {})
                
                # 如果只要求主HTML，设置dom为main_html
                if selector == 'html':
                    result['dom'] = dom['main_html']
                else:
                    # 如果查询特定元素，保持原有行为
                    result['dom'] = dom
                    
                # 添加大小信息
                if isinstance(result['dom'], str):
                    result['size'] = len(result['dom'])
                else:
                    # 计算总大小
                    main_size = len(dom['main_html']) if isinstance(dom['main_html'], str) else 0
                    iframe_size = sum(len(iframe_data['html']) if isinstance(iframe_data['html'], str) else 0 
                                    for iframe_data in dom.get('iframes', {}).values())
                    result['size'] = main_size + iframe_size
            else:
                # 普通字符串DOM
                result['dom'] = dom
                result['size'] = len(dom) if isinstance(dom, str) else 0
                
            result['success'] = True
            result['message'] = f"成功获取页面 {page_index} 的DOM结构"
            
            if result['has_iframes']:
                result['message'] += f"，包含 {result['iframe_count']} 个iframe内容"
                
            return result
            
        except Exception as e:
            import traceback
            print(f"[错误] 获取DOM时发生异常: {str(e)}")
            print(traceback.format_exc())
            result['message'] = f"获取页面DOM时发生异常: {str(e)}"
            return result
    
    async def _get_element_html(self, page, selector, timeout=10000):
        """获取特定元素的HTML内容"""
        try:
            # 等待元素出现
            await page.wait_for_selector(selector, timeout=timeout)
            
            # 使用JavaScript获取元素HTML
            js_code = """
            (selector) => {
                try {
                    const element = document.querySelector(selector);
                    if (!element) return null;
                    return element.outerHTML;
                } catch (e) {
                    console.error('获取元素HTML出错:', e);
                    return null;
                }
            }
            """
            
            html = await page.evaluate(js_code, selector)
            if not html:
                # 尝试备用方法
                try:
                    element_handle = await page.query_selector(selector)
                    if element_handle:
                        html = await page.evaluate("element => element.outerHTML", element_handle)
                        await element_handle.dispose()  # 释放资源
                except Exception as backup_error:
                    print(f"[警告] 备用方法获取元素HTML失败: {str(backup_error)}")
                    return None
                    
            return html
        except Exception as e:
            print(f"[错误] 获取元素HTML时出错: {str(e)}")
            return None
        
    async def _get_full_page_html(self, page, include_iframes=True, iframe_depth=3):
        """
        获取完整页面的HTML内容，包括iframe内容
        
        Args:
            page: Playwright页面对象
            include_iframes: 是否包含iframe内容
            iframe_depth: iframe递归获取的最大深度
            
        Returns:
            完整的HTML内容
        """
        # 策略1: 先获取主页面的HTML
        try:
            # 等待页面加载完成
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception as wait_error:
                print(f"[警告] 等待页面加载完成超时: {str(wait_error)}")
                # 继续尝试获取DOM
            
            # 使用JavaScript直接获取DOM
            js_code = """
            () => {
                // 等待页面稳定并获取完整DOM
                return new Promise((resolve) => {
                    // 如果页面已加载，直接返回DOM
                    if (document.readyState === 'complete') {
                        setTimeout(() => {
                            resolve(document.documentElement.outerHTML);
                        }, 500);
                    } else {
                        // 等待页面加载完成
                        window.addEventListener('load', () => {
                            setTimeout(() => {
                                resolve(document.documentElement.outerHTML);
                            }, 500);
                        });
                    }
                });
            }
            """
            
            main_html = await page.evaluate(js_code)
            if not main_html or len(main_html) < 100:  # 检查内容是否有效
                # 尝试备用方法
                try:
                    main_html = await page.content()
                except Exception as content_error:
                    print(f"[警告] 标准方法获取DOM失败: {str(content_error)}")
                    # 最后尝试简化方法
                    try:
                        main_html = await page.evaluate("() => document.documentElement.outerHTML")
                    except Exception:
                        print("[错误] 所有获取主页面HTML的方法都失败")
                        return None
            
            # 如果不需要处理iframe，直接返回主页面HTML
            if not include_iframes:
                return main_html
                
            # 处理iframe内容
            try:
                # 查找所有iframe元素
                iframe_handles = await page.query_selector_all('iframe')
                if not iframe_handles:
                    print("[信息] 页面中未找到iframe元素")
                    return main_html
                
                print(f"[信息] 找到 {len(iframe_handles)} 个iframe元素，开始处理...")
                
                # 创建一个字典存储iframe内容
                iframe_contents = {}
                
                # 遍历处理每个iframe
                for i, iframe_handle in enumerate(iframe_handles):
                    if iframe_depth <= 0:
                        continue  # 超过最大递归深度，跳过
                        
                    try:
                        # 获取iframe的关键属性
                        iframe_id = await iframe_handle.get_attribute('id') or f"iframe_{i}"
                        iframe_src = await iframe_handle.get_attribute('src')
                        iframe_name = await iframe_handle.get_attribute('name') or iframe_id
                        
                        print(f"[信息] 处理iframe: {iframe_name}, src: {iframe_src}")
                        
                        # 判断iframe是否可访问
                        if not iframe_src or iframe_src.startswith('javascript:') or iframe_src == 'about:blank':
                            print(f"[信息] 跳过空iframe或JavaScript iframe: {iframe_name}")
                            continue
                            
                        # 获取iframe的内容框架对象
                        content_frame = await iframe_handle.content_frame()
                        if not content_frame:
                            print(f"[警告] 无法获取iframe内容框架: {iframe_name}")
                            continue
                            
                        # 等待iframe内容加载
                        try:
                            await content_frame.wait_for_load_state("networkidle", timeout=3000)
                        except Exception as iframe_wait_error:
                            print(f"[警告] 等待iframe加载超时: {str(iframe_wait_error)}")
                            
                        # 递归获取iframe内容，减少深度
                        iframe_html = await self._get_full_page_html(
                            content_frame, 
                            include_iframes=True, 
                            iframe_depth=iframe_depth-1
                        )
                        
                        if iframe_html:
                            iframe_contents[iframe_name] = {
                                'id': iframe_id,
                                'src': iframe_src,
                                'name': iframe_name,
                                'html': iframe_html
                            }
                            print(f"[成功] 获取iframe内容: {iframe_name}, 大小: {len(iframe_html)} 字符")
                        else:
                            print(f"[警告] 未能获取iframe内容: {iframe_name}")
                            
                    except Exception as iframe_error:
                        print(f"[错误] 处理iframe时出错: {str(iframe_error)}")
                        continue
                    finally:
                        # 释放iframe句柄资源
                        await iframe_handle.dispose()
                
                # 将iframe内容信息添加到结果中
                if iframe_contents:
                    # 创建一个包含完整信息的结构
                    enhanced_content = {
                        'main_html': main_html,
                        'iframes': iframe_contents,
                        'iframe_count': len(iframe_contents)
                    }
                    return enhanced_content
                
                # 如果没有成功获取iframe内容，返回主页面HTML
                return main_html
                
            except Exception as iframe_process_error:
                print(f"[错误] 处理iframe过程中发生异常: {str(iframe_process_error)}")
                # 出错时至少返回主页面内容
                return main_html
                
        except Exception as e:
            print(f"[错误] 获取页面HTML时发生异常: {str(e)}")
            return None
    
    def get_page_dom(self, page_index: int, selector: str = 'html') -> Dict[str, Any]:
        """
        获取指定页面的DOM结构
        
        Args:
            page_index: 页面序号（从0开始）
            selector: CSS选择器，默认为'html'（整个页面）
            
        Returns:
            包含DOM结构的结果信息
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': "未连接到浏览器，请先连接"
            }
        
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        try:
            return self._async_loop.run_until_complete(
                self._get_page_dom_async(page_index, selector)
            )
        except Exception as e:
            return {
                'success': False,
                'message': f"执行获取DOM时出错: {str(e)}"
            }
    
    async def _get_clickable_elements_async(self, page_index: int, include_iframes: bool = True) -> Dict[str, Any]:
        """
        异步获取指定页面所有可点击的元素
        
        Args:
            page_index: 页面序号（从0开始）
            include_iframes: 是否包含iframe中的元素
            
        Returns:
            包含可点击元素的结果信息
        """
        result = {
            'success': False,
            'message': '',
            'title': None,
            'url': None,
            'elements': []
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        if not self.context:
            result['message'] = "无法获取浏览器上下文"
            return result
            
        # 获取所有页面
        pages = self.context.pages
        
        # 检查页面序号是否有效
        if page_index < 0 or page_index >= len(pages):
            result['message'] = f"无效的页面序号: {page_index}，有效范围: 0-{len(pages)-1}"
            return result
        
        try:
            # 获取指定序号的页面
            target_page = pages[page_index]
            
            # 获取页面标题和URL
            title = await target_page.title()
            url = target_page.url
            
            # 将这些信息添加到结果中
            result['title'] = title
            result['url'] = url
            
            # 首先获取主页面的可点击元素
            main_page_elements = await self._get_clickable_elements_in_context(target_page)
            elements = main_page_elements
            
            # 如果需要包含iframe中的元素
            if include_iframes:
                try:
                    # 查找所有iframe元素
                    iframe_handles = await target_page.query_selector_all('iframe')
                    
                    if iframe_handles:
                        print(f"[信息] 发现 {len(iframe_handles)} 个iframe，正在获取iframe内可点击元素...")
                        
                        # 遍历处理每个iframe
                        for i, iframe_handle in enumerate(iframe_handles):
                            try:
                                # 获取iframe信息
                                iframe_id = await iframe_handle.get_attribute('id') or f"iframe_{i}"
                                iframe_name = await iframe_handle.get_attribute('name') or iframe_id
                                iframe_src = await iframe_handle.get_attribute('src') or ""
                                
                                print(f"[信息] 处理iframe: {iframe_name}, src: {iframe_src}")
                                
                                # 获取iframe的内容框架
                                content_frame = await iframe_handle.content_frame()
                                if not content_frame:
                                    print(f"[警告] 无法获取iframe '{iframe_name}' 的内容框架")
                                    continue
                                    
                                # 从iframe中获取可点击元素
                                iframe_elements = await self._get_clickable_elements_in_context(content_frame)
                                
                                # 获取iframe的位置信息
                                try:
                                    iframe_rect = await iframe_handle.bounding_box()
                                except:
                                    iframe_rect = None
                                
                                # 为iframe中的元素添加标记和信息
                                for element in iframe_elements:
                                    element['from_iframe'] = True
                                    element['iframe_id'] = iframe_id
                                    element['iframe_name'] = iframe_name
                                    element['iframe_src'] = iframe_src
                                    element['iframe_index'] = i
                                    
                                    if iframe_rect:
                                        element['iframe_rect'] = iframe_rect
                                        
                                        # 调整元素位置，将iframe中的相对位置转换为页面中的绝对位置
                                        if 'rect' in element:
                                            element_rect = element['rect']
                                            # 计算绝对坐标
                                            absolute_rect = {
                                                'x': iframe_rect['x'] + element_rect['x'],
                                                'y': iframe_rect['y'] + element_rect['y'],
                                                'width': element_rect['width'],
                                                'height': element_rect['height'],
                                                'top': iframe_rect['y'] + element_rect['top'],
                                                'left': iframe_rect['x'] + element_rect['left'],
                                                'bottom': iframe_rect['y'] + element_rect['bottom'],
                                                'right': iframe_rect['x'] + element_rect['right']
                                            }
                                            # 保存原始相对坐标
                                            element['relative_rect'] = element_rect.copy() 
                                            # 更新为绝对坐标
                                            element['rect'] = absolute_rect
                                
                                # 添加到总元素列表
                                elements.extend(iframe_elements)
                                print(f"[信息] 在iframe '{iframe_name}' 中找到 {len(iframe_elements)} 个可点击元素")
                                
                            except Exception as e:
                                print(f"[警告] 处理iframe '{iframe_name}' 时出错: {str(e)}")
                            finally:
                                # 释放iframe句柄资源
                                await iframe_handle.dispose()
                except Exception as e:
                    print(f"[警告] 处理iframe时出错: {str(e)}")
                    # 继续使用主页面的元素
            
            # 设置结果
            result['success'] = True
            result['message'] = f"找到 {len(elements)} 个可点击元素"
            result['elements'] = elements
            
            return result
        
        except Exception as e:
            import traceback
            print(f"获取可点击元素时出错: {str(e)}")
            print(traceback.format_exc())
            result['message'] = f"获取可点击元素时出错: {str(e)}"
            return result

    async def _get_clickable_elements_in_context(self, context) -> List[Dict]:
        """
        在指定上下文（页面或iframe）中获取可点击元素
        
        Args:
            context: 页面或iframe上下文
            
        Returns:
            可点击元素列表
        """
        # 构建查询可点击元素的JavaScript代码
        js_code = """
        () => {
            // 查找所有可能的可点击元素
            const clickableElements = [];
            
            // 1. 查找所有a标签（链接）
            const links = Array.from(document.querySelectorAll('a'));
            links.forEach(link => {
                const rect = link.getBoundingClientRect();
                
                // 跳过隐藏元素和面积过小的元素
                if (rect.width < 2 || rect.height < 2 || 
                    link.style.display === 'none' || 
                    link.style.visibility === 'hidden' ||
                    link.style.opacity === '0') {
                    return;
                }
                
                // 获取元素文本
                const text = link.innerText || link.textContent || '';
                
                // 获取所有属性
                const attributes = {};
                for (const attr of link.attributes) {
                    attributes[attr.name] = attr.value;
                }
                
                // 获取链接地址
                const href = link.getAttribute('href');
                
                // 获取计算样式
                const style = window.getComputedStyle(link);
                const bgColor = style.backgroundColor;
                const textColor = style.color;
                
                // 创建元素描述
                clickableElements.push({
                    type: 'link',
                    tagName: link.tagName,
                    text: text.trim(),
                    href: href,
                    cssSelector: getCssSelector(link),
                    xpath: getXPath(link),
                    rect: {
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        top: rect.top,
                        left: rect.left,
                        bottom: rect.bottom,
                        right: rect.right
                    },
                    attributes: attributes,
                    style: {
                        backgroundColor: bgColor,
                        color: textColor
                    }
                });
            });
            
            // 2. 查找所有button标签和type="button"的input标签
            const buttons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"]'));
            buttons.forEach(button => {
                const rect = button.getBoundingClientRect();
                
                // 跳过隐藏元素和面积过小的元素
                if (rect.width < 2 || rect.height < 2 || 
                    button.style.display === 'none' || 
                    button.style.visibility === 'hidden' ||
                    button.style.opacity === '0') {
                    return;
                }
                
                // 获取元素文本
                let text = '';
                let value = '';
                
                if (button.tagName === 'INPUT') {
                    text = button.value || button.placeholder || '';
                    value = button.value || '';
                } else {
                    text = button.innerText || button.textContent || '';
                }
                
                // 获取所有属性
                const attributes = {};
                for (const attr of button.attributes) {
                    attributes[attr.name] = attr.value;
                }
                
                // 获取计算样式
                const style = window.getComputedStyle(button);
                const bgColor = style.backgroundColor;
                const textColor = style.color;
                
                // 创建元素描述
                clickableElements.push({
                    type: 'button',
                    tagName: button.tagName,
                    text: text.trim(),
                    value: value,
                    cssSelector: getCssSelector(button),
                    xpath: getXPath(button),
                    rect: {
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        top: rect.top,
                        left: rect.left,
                        bottom: rect.bottom,
                        right: rect.right
                    },
                    attributes: attributes,
                    style: {
                        backgroundColor: bgColor,
                        color: textColor
                    }
                });
            });
            
            // 3. 查找具有click事件的元素（div、span等）
            const potentialElements = Array.from(document.querySelectorAll('div, span, img, svg, li, label'));
            potentialElements.forEach(el => {
                // 判断是否有点击事件监听器或cursor:pointer样式
                const style = window.getComputedStyle(el);
                const isClickable = style.cursor === 'pointer';
                
                if (isClickable) {
                    const rect = el.getBoundingClientRect();
                    
                    // 跳过隐藏元素和面积过小的元素
                    if (rect.width < 2 || rect.height < 2 || 
                        el.style.display === 'none' || 
                        el.style.visibility === 'hidden' ||
                        el.style.opacity === '0') {
                        return;
                    }
                    
                    // 获取元素文本
                    const text = el.innerText || el.textContent || '';
                    
                    // 对于图片，获取alt和title
                    let alt = '';
                    if (el.tagName === 'IMG') {
                        alt = el.getAttribute('alt') || '';
                    }
                    
                    // 获取所有属性
                    const attributes = {};
                    for (const attr of el.attributes) {
                        attributes[attr.name] = attr.value;
                    }
                    
                    // 获取计算样式
                    const bgColor = style.backgroundColor;
                    const textColor = style.color;
                    
                    // 创建元素描述
                    clickableElements.push({
                        type: 'element',
                        tagName: el.tagName,
                        text: text.trim(),
                        alt: alt,
                        cssSelector: getCssSelector(el),
                        xpath: getXPath(el),
                        rect: {
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height,
                            top: rect.top,
                            left: rect.left,
                            bottom: rect.bottom,
                            right: rect.right
                        },
                        attributes: attributes,
                        style: {
                            backgroundColor: bgColor,
                            color: textColor
                        }
                    });
                }
            });
            
            // 4. 查找具有role="button"等可交互角色的元素
            const roleElements = Array.from(document.querySelectorAll('[role="button"], [role="link"], [role="tab"], [role="menuitem"]'));
            roleElements.forEach(el => {
                const rect = el.getBoundingClientRect();
                
                // 跳过隐藏元素和面积过小的元素
                if (rect.width < 2 || rect.height < 2 || 
                    el.style.display === 'none' || 
                    el.style.visibility === 'hidden' ||
                    el.style.opacity === '0') {
                    return;
                }
                
                // 获取元素文本
                const text = el.innerText || el.textContent || '';
                
                // 获取角色
                const role = el.getAttribute('role');
                
                // 获取所有属性
                const attributes = {};
                for (const attr of el.attributes) {
                    attributes[attr.name] = attr.value;
                }
                
                // 获取计算样式
                const style = window.getComputedStyle(el);
                const bgColor = style.backgroundColor;
                const textColor = style.color;
                
                // 创建元素描述
                clickableElements.push({
                    type: 'role',
                    role: role,
                    tagName: el.tagName,
                    text: text.trim(),
                    cssSelector: getCssSelector(el),
                    xpath: getXPath(el),
                    rect: {
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        top: rect.top,
                        left: rect.left,
                        bottom: rect.bottom,
                        right: rect.right
                    },
                    attributes: attributes,
                    style: {
                        backgroundColor: bgColor,
                        color: textColor
                    }
                });
            });
            
            // 辅助函数：获取CSS选择器
            function getCssSelector(element) {
                if (!element) return '';
                
                let path = [];
                while (element.nodeType === Node.ELEMENT_NODE) {
                    let selector = element.nodeName.toLowerCase();
                    
                    if (element.id) {
                        selector += '#' + element.id;
                        path.unshift(selector);
                        break;
                    } else {
                        let sibling = element;
                        let index = 1;
                        
                        while (sibling = sibling.previousElementSibling) {
                            if (sibling.nodeName.toLowerCase() === selector) {
                                index++;
                            }
                        }
                        
                        if (index > 1) {
                            selector += ':nth-of-type(' + index + ')';
                        }
                    }
                    
                    path.unshift(selector);
                    element = element.parentNode;
                }
                
                return path.join(' > ');
            }
            
            // 辅助函数：获取XPath
            function getXPath(element) {
                if (!element) return '';
                
                let xpath = '';
                let current = element;
                
                while (current && current.nodeType === Node.ELEMENT_NODE) {
                    let index = 0;
                    let hasFollowingSibling = false;
                    
                    for (let sibling = current.previousSibling; sibling; sibling = sibling.previousSibling) {
                        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === current.tagName) {
                            index++;
                        }
                    }
                    
                    let tagCount = 1;
                    for (let sibling = current.nextSibling; sibling && !hasFollowingSibling; sibling = sibling.nextSibling) {
                        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === current.tagName) {
                            hasFollowingSibling = true;
                            tagCount++;
                        }
                    }
                    
                    const pathIndex = (index > 0 || hasFollowingSibling) ? '[' + (index + 1) + ']' : '';
                    xpath = '/' + current.tagName.toLowerCase() + pathIndex + xpath;
                    
                    current = current.parentNode;
                }
                
                return xpath;
            }
            
            return clickableElements;
        }
        """
        
        try:
            # 执行查询脚本
            elements = await context.evaluate(js_code)
            return elements
        except Exception as e:
            print(f"[错误] 获取上下文中的可点击元素时出错: {str(e)}")
            return []

    def get_clickable_elements(self, page_index: int, include_iframes: bool = True) -> Dict[str, Any]:
        """
        获取指定页面所有可点击的元素
        
        Args:
            page_index: 页面序号（从0开始）
            include_iframes: 是否包含iframe中的元素
            
        Returns:
            包含可点击元素的结果信息
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': "未连接到浏览器，请先连接"
            }
        
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        try:
            return self._async_loop.run_until_complete(
                self._get_clickable_elements_async(page_index, include_iframes)
            )
        except Exception as e:
            return {
                'success': False,
                'message': f"执行获取可点击元素时出错: {str(e)}"
            }
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            
        Returns:
            相似度得分 (0-1)
        """
        # 如果RAG工具可用，使用RAG工具计算相似度
        if self.rag_tool is not None:
            try:
                similarity_result = self.rag_tool.calculate_similarity(text1, text2)
                if similarity_result.get("success", False):
                    return similarity_result.get("similarity", 0.0)
            except Exception as e:
                print(f"使用RAG工具计算相似度时出错: {e}")
        
        # 回退到简单的相似度计算方法
        # 把文本转换为小写，并去除首尾空白
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # 如果有一个文本为空，返回0
        if not text1 or not text2:
            return 0.0
            
        # 如果文本相同，返回1
        if text1 == text2:
            return 1.0
        
        # 计算包含关系
        if text1 in text2 or text2 in text1:
            return 0.8
            
        # 计算词集合的交集
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        # 如果词集合为空，比较字符重叠
        if not words1 or not words2:
            # 字符重叠
            common_chars = set(text1) & set(text2)
            total_chars = set(text1) | set(text2)
            return len(common_chars) / len(total_chars) if total_chars else 0.0
        
        # 计算Jaccard相似度
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    async def _find_elements_by_similarity_async(self, page_index: int, text: str, element_types: List[str] = None, 
                                         similarity_threshold: float = 0.75, max_results: int = 5,
                                         include_iframes: bool = True) -> Dict[str, Any]:
        """
        异步获取与指定文本相似的元素列表
        
        Args:
            page_index: 页面序号（从0开始）
            text: 要查找的文本
            element_types: 元素类型列表，如['button', 'a', 'input']
            similarity_threshold: 相似度阈值（0-1）
            max_results: 最大结果数量
            include_iframes: 是否在iframe中查找元素
            
        Returns:
            包含查找结果的字典
        """
        result = {
            'success': False,
            'message': '',
            'title': None,
            'url': None,
            'elements': [],
            'similarities': []
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        if not self.context:
            result['message'] = "无法获取浏览器上下文"
            return result
        
        if not text or not text.strip():
            result['message'] = "搜索文本不能为空"
            return result
        
        # 规范化元素类型
        if not element_types:
            element_types = ['button', 'a', 'div', 'span', 'li', 'input']
        
        # 获取所有页面
        pages = self.context.pages
        
        # 检查页面序号是否有效
        if page_index < 0 or page_index >= len(pages):
            result['message'] = f"无效的页面序号: {page_index}，有效范围: 0-{len(pages)-1}"
            return result
        
        try:
            # 获取指定序号的页面
            target_page = pages[page_index]
            
            # 获取页面标题和URL
            title = await target_page.title()
            url = target_page.url
            
            # 将这些信息添加到结果中
            result['title'] = title
            result['url'] = url
            
            # 搜索相似元素 - 首先在主页面搜索
            main_page_elements = await self._search_elements_in_context(
                target_page, text, element_types, similarity_threshold, max_results
            )
            
            found_elements = main_page_elements['elements']
            found_similarities = main_page_elements['similarities']
            
            # 如果需要在iframe中搜索
            if include_iframes and len(found_elements) < max_results:
                try:
                    # 查找所有iframe
                    iframe_handles = await target_page.query_selector_all('iframe')
                    
                    if iframe_handles:
                        print(f"[信息] 在 {len(iframe_handles)} 个iframe中查找元素...")
                        
                        # 遍历每个iframe
                        for i, iframe_handle in enumerate(iframe_handles):
                            if len(found_elements) >= max_results:
                                break
                                
                            try:
                                # 获取iframe的内容框架
                                content_frame = await iframe_handle.content_frame()
                                if not content_frame:
                                    continue
                                    
                                # 获取iframe信息
                                iframe_id = await iframe_handle.get_attribute('id') or f"iframe_{i}"
                                iframe_name = await iframe_handle.get_attribute('name') or iframe_id
                                    
                                print(f"[信息] 在iframe '{iframe_name}' 中查找元素...")
                                
                                # 在iframe中搜索元素
                                iframe_max_results = max_results - len(found_elements)
                                iframe_results = await self._search_elements_in_context(
                                    content_frame, text, element_types, 
                                    similarity_threshold, iframe_max_results
                                )
                                
                                if iframe_results['elements']:
                                    print(f"[信息] 在iframe '{iframe_name}' 中找到 {len(iframe_results['elements'])} 个匹配元素")
                                    
                                    # 为来自iframe的元素添加标记
                                    for j, iframe_element in enumerate(iframe_results['elements']):
                                        iframe_element['from_iframe'] = True
                                        iframe_element['iframe_id'] = iframe_id
                                        iframe_element['iframe_name'] = iframe_name
                                        iframe_element['iframe_index'] = i
                                        
                                        # 获取iframe的位置，用于辅助定位
                                        try:
                                            iframe_rect = await iframe_handle.bounding_box()
                                            iframe_element['iframe_rect'] = iframe_rect
                                        except:
                                            pass
                                    
                                    # 添加到主结果中
                                    found_elements.extend(iframe_results['elements'])
                                    found_similarities.extend(iframe_results['similarities'])
                            except Exception as iframe_error:
                                print(f"[警告] 处理iframe时出错: {str(iframe_error)}")
                            finally:
                                # 释放iframe句柄
                                await iframe_handle.dispose()
                except Exception as e:
                    print(f"[警告] 处理iframe查找时出错: {str(e)}")
                    # 继续使用主页面的结果
            
            # 如果找到了元素
            if found_elements:
                # 对结果按相似度排序
                sorted_elements = [x for _, x in sorted(
                    zip(found_similarities, found_elements), 
                    key=lambda pair: pair[0], 
                    reverse=True
                )]
                sorted_similarities = sorted(found_similarities, reverse=True)
                
                # 添加到结果中
                result['elements'] = sorted_elements[:max_results]
                result['similarities'] = sorted_similarities[:max_results]
                result['success'] = True
                result['message'] = f"找到 {len(result['elements'])} 个相似元素"
            else:
                result['message'] = f"未找到与 '{text}' 相似的元素"
            
            return result
            
        except Exception as e:
            import traceback
            print(f"查找相似元素时出错: {str(e)}")
            print(traceback.format_exc())
            result['message'] = f"查找相似元素时出错: {str(e)}"
            return result

    async def _search_elements_in_context(self, context, text: str, element_types: List[str], 
                                         similarity_threshold: float, max_results: int) -> Dict[str, Any]:
        """
        在指定上下文（页面或iframe）中搜索元素
        
        Args:
            context: 页面或iframe上下文
            text: 要查找的文本
            element_types: 元素类型列表
            similarity_threshold: 相似度阈值
            max_results: 最大结果数量
            
        Returns:
            包含元素和相似度的字典
        """
        result = {
            'elements': [],
            'similarities': []
        }
        
        # 确保text是字符串
        if not isinstance(text, str):
            text = str(text)
        
        text = text.lower().strip()
        
        # 构建JavaScript查询函数，将参数内置到JS代码中
        js_code = """
        (searchParams) => {
            const types = searchParams.types;
            const searchText = searchParams.text;
            const threshold = searchParams.threshold;
            const maxResults = searchParams.maxResults;
            
            // 相似度计算函数
            function similarity(s1, s2) {
                s1 = s1.toLowerCase().trim();
                s2 = s2.toLowerCase().trim();
                
                if (s1 === s2) return 1.0;
                if (s1.includes(s2) || s2.includes(s1)) {
                    return Math.min(s1.length, s2.length) / Math.max(s1.length, s2.length);
                }
                
                // 简单相似度计算 - 可以用更复杂的算法替换
                let matches = 0;
                const words1 = s1.split(/\\s+/);
                const words2 = s2.split(/\\s+/);
                
                for (const w1 of words1) {
                    if (w1.length <= 1) continue;
                    for (const w2 of words2) {
                        if (w2.length <= 1) continue;
                        if (w1 === w2 || w1.includes(w2) || w2.includes(w1)) {
                            matches++;
                            break;
                        }
                    }
                }
                
                return matches / Math.max(1, Math.max(words1.length, words2.length));
            }
            
            // 根据提供的类型查找所有可能的元素
            let allElements = [];
            for (const type of types) {
                if (type === 'a' || type === 'button' || type === 'input') {
                    // 针对链接、按钮和输入框的查询
                    const elements = Array.from(document.querySelectorAll(type));
                    allElements = allElements.concat(elements);
                } else {
                    // 针对其他任意元素的查询
                    const elements = Array.from(document.querySelectorAll(type));
                    allElements = allElements.concat(elements);
                }
            }
            
            // 处理添加具有角色的元素
            const roleElements = Array.from(document.querySelectorAll('[role="button"], [role="link"], [role="tab"], [role="menuitem"]'));
            allElements = allElements.concat(roleElements);
            
            // 查找包含特定文本的元素，添加到候选列表
            const candidates = [];
            
            for (const el of allElements) {
                // 针对不同类型的元素获取文本内容
                let elementText = '';
                let valueText = '';
                
                // 获取元素的文本内容
                elementText = el.innerText || el.textContent || '';
                
                // 对于输入框，获取value或placeholder
                if (el.tagName === 'INPUT') {
                    valueText = el.value || el.placeholder || '';
                }
                
                // 获取aria标签和title
                const ariaLabel = el.getAttribute('aria-label') || '';
                const title = el.getAttribute('title') || '';
                
                // 合并所有可能的文本来源
                const combinedText = [elementText, valueText, ariaLabel, title].filter(t => t).join(' ');
                
                if (combinedText.trim()) {
                    // 计算相似度
                    const sim = similarity(combinedText, searchText);
                    
                    if (sim >= threshold) {
                        // 创建元素的基本信息
                        const rect = el.getBoundingClientRect();
                        const styles = window.getComputedStyle(el);
                        
                        // 获取计算的颜色
                        const bgColor = styles.backgroundColor;
                        const textColor = styles.color;
                        const isVisible = !(styles.display === 'none' || styles.visibility === 'hidden' || styles.opacity === '0');
                        
                        // 获取元素的所有属性
                        const attributes = {};
                        for (const attr of el.attributes) {
                            attributes[attr.name] = attr.value;
                        }
                        
                        // 创建元素描述对象
                        const elementInfo = {
                            type: el.tagName.toLowerCase(),
                            text: elementText.trim(),
                            value: valueText.trim(),
                            ariaLabel: ariaLabel,
                            title: title,
                            combinedText: combinedText.trim(),
                            similarity: sim,
                            cssSelector: getCssSelector(el),
                            xpath: getXPath(el),
                            rect: {
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height,
                                top: rect.top,
                                left: rect.left,
                                bottom: rect.bottom,
                                right: rect.right
                            },
                            isVisible: isVisible,
                            style: {
                                backgroundColor: bgColor,
                                color: textColor,
                                display: styles.display,
                                visibility: styles.visibility,
                                opacity: styles.opacity
                            },
                            attributes: attributes,
                            html: el.outerHTML.substring(0, 500) // 限制HTML长度
                        };
                        
                        candidates.push({
                            element: elementInfo,
                            similarity: sim
                        });
                    }
                }
            }
            
            // 根据相似度排序候选项
            candidates.sort((a, b) => b.similarity - a.similarity);
            
            // 返回指定数量的结果
            const results = candidates.slice(0, maxResults);
            
            // 辅助函数：获取CSS选择器
            function getCssSelector(element) {
                if (!element) return '';
                
                let path = [];
                while (element.nodeType === Node.ELEMENT_NODE) {
                    let selector = element.nodeName.toLowerCase();
                    
                    if (element.id) {
                        selector += '#' + element.id;
                        path.unshift(selector);
                        break;
                    } else {
                        let sibling = element;
                        let index = 1;
                        while (sibling = sibling.previousElementSibling) {
                            if (sibling.nodeName.toLowerCase() === selector) {
                                index++;
                            }
                        }
                        if (index > 1) {
                            selector += ':nth-of-type(' + index + ')';
                        }
                    }
                    
                    path.unshift(selector);
                    element = element.parentNode;
                }
                
                return path.join(' > ');
            }
            
            // 辅助函数：获取XPath
            function getXPath(element) {
                if (!element) return '';
                
                let xpath = '';
                let current = element;
                
                while (current && current.nodeType === Node.ELEMENT_NODE) {
                    let index = 0;
                    let hasFollowingSibling = false;
                    
                    for (let sibling = current.previousSibling; sibling; sibling = sibling.previousSibling) {
                        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === current.tagName) {
                            index++;
                        }
                    }
                    
                    let tagCount = 1;
                    for (let sibling = current.nextSibling; sibling && !hasFollowingSibling; sibling = sibling.nextSibling) {
                        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === current.tagName) {
                            hasFollowingSibling = true;
                            tagCount++;
                        }
                    }
                    
                    const pathIndex = (index > 0 || hasFollowingSibling) ? '[' + (index + 1) + ']' : '';
                    xpath = '/' + current.tagName.toLowerCase() + pathIndex + xpath;
                    
                    current = current.parentNode;
                }
                
                return xpath;
            }
            
            return {
                elements: results.map(r => r.element),
                similarities: results.map(r => r.similarity)
            };
        }
        """
        
        try:
            # 按照Playwright的API要求构建参数对象
            search_params = {
                'types': element_types,
                'text': text,
                'threshold': similarity_threshold,
                'maxResults': max_results
            }
            
            # 使用正确的参数调用evaluate
            result = await context.evaluate(js_code, search_params)
            return result
        except Exception as e:
            print(f"[错误] 在上下文中搜索元素时出错: {str(e)}")
            return {'elements': [], 'similarities': []}

    def find_elements_by_similarity(self, page_index: int, text: str, element_types: List[str] = None, 
                                   similarity_threshold: float = 0.75, max_results: int = 5,
                                   include_iframes: bool = True) -> Dict[str, Any]:
        """
        获取与指定文本相似的元素列表
        
        Args:
            page_index: 页面序号（从0开始）
            text: 要查找的文本
            element_types: 元素类型列表，如['button', 'a', 'input']
            similarity_threshold: 相似度阈值（0-1）
            max_results: 最大结果数量
            include_iframes: 是否在iframe中查找元素
            
        Returns:
            包含查找结果的字典
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': "未连接到浏览器，请先连接"
            }
        
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        try:
            return self._async_loop.run_until_complete(
                self._find_elements_by_similarity_async(
                    page_index, text, element_types, 
                    similarity_threshold, max_results, include_iframes
                )
            )
        except Exception as e:
            return {
                'success': False,
                'message': f"执行查找元素时出错: {str(e)}"
            }
    
    async def _click_element_async(self, page_index: int, element_selector: str, 
                                 click_type: str = 'click', wait_for_navigation: bool = True) -> Dict[str, Any]:
        """
        异步点击指定元素
        
        Args:
            page_index: 页面序号（从0开始）
            element_selector: 元素选择器 (CSS或XPath)
            click_type: 点击类型 (click, dblclick, hover)
            wait_for_navigation: 是否等待页面导航完成
            
        Returns:
            点击操作结果
        """
        result = {
            'success': False,
            'message': '',
            'title': None,
            'url': None
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        if not self.context:
            result['message'] = "无法获取浏览器上下文"
            return result
            
        # 获取所有页面
        pages = self.context.pages
        
        # 检查页面序号是否有效
        if page_index < 0 or page_index >= len(pages):
            result['message'] = f"无效的页面序号: {page_index}，有效范围: 0-{len(pages)-1}"
            return result
        
        try:
            # 获取指定序号的页面
            target_page = pages[page_index]
            
            # 记录初始标题和URL以检测变化
            initial_title = await target_page.title()
            initial_url = target_page.url
            
            # 尝试不同策略定位元素
            element = None
            error_message = ""
            
            # 判断是CSS还是XPath选择器
            is_xpath = element_selector.startswith('/')
            
            try:
                # 1. 首先尝试原始选择器
                if is_xpath:
                    # XPath选择器
                    element = await target_page.wait_for_selector(f"xpath={element_selector}", timeout=3000)
                else:
                    # CSS选择器
                    element = await target_page.wait_for_selector(element_selector, timeout=3000)
            except PlaywrightError as e:
                error_message = str(e)
                # 如果是CSS选择器，尝试简化它
                if not is_xpath and '>' in element_selector:
                    try:
                        # 2. 尝试使用更简单的选择器（去除父元素部分）
                        simplified_selector = element_selector.split('>')[-1].strip()
                        element = await target_page.wait_for_selector(simplified_selector, timeout=3000)
                    except PlaywrightError:
                        pass
                        
                # 如果仍然失败，尝试使用JS查询元素
                if not element:
                    try:
                        # 3. 使用JavaScript直接查询元素
                        js_code = """(selector) => {
                            try {
                                const isXpath = selector.startsWith('/');
                                let element = null;
                                
                                if (isXpath) {
                                    // XPath查询
                                    const result = document.evaluate(
                                        selector, 
                                        document, 
                                        null, 
                                        XPathResult.FIRST_ORDERED_NODE_TYPE, 
                                        null
                                    );
                                    element = result.singleNodeValue;
                                } else {
                                    // CSS查询
                                    element = document.querySelector(selector);
                                    
                                    // 如果没找到，尝试简化选择器
                                    if (!element && selector.includes('>')) {
                                        const simplified = selector.split('>').pop().trim();
                                        element = document.querySelector(simplified);
                                    }
                                }
                                
                                // 如果找到了元素，将其高亮并滚动到视图中
                                if (element) {
                                    const originalBackground = element.style.backgroundColor;
                                    const originalOutline = element.style.outline;
                                    
                                    element.style.backgroundColor = 'rgba(255, 0, 0, 0.3)';
                                    element.style.outline = '2px solid red';
                                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    
                                    // 3秒后恢复原样
                                    setTimeout(() => {
                                        element.style.backgroundColor = originalBackground;
                                        element.style.outline = originalOutline;
                                    }, 3000);
                                    
                                    return true; // 元素存在
                                }
                                
                                return false; // 元素不存在
                            } catch (error) {
                                console.error('查找元素出错:', error);
                                return false;
                            }
                        }"""
                        
                        element_exists = await target_page.evaluate(js_code, element_selector)
                        
                        if element_exists:
                            # 4. 如果元素存在，使用evaluate_handle来获取元素句柄
                            js_get_element = """(selector) => {
                                const isXpath = selector.startsWith('/');
                                if (isXpath) {
                                    const result = document.evaluate(
                                        selector, 
                                        document, 
                                        null, 
                                        XPathResult.FIRST_ORDERED_NODE_TYPE, 
                                        null
                                    );
                                    return result.singleNodeValue;
                                } else {
                                    let el = document.querySelector(selector);
                                    if (!el && selector.includes('>')) {
                                        const simplified = selector.split('>').pop().trim();
                                        el = document.querySelector(simplified);
                                    }
                                    return el;
                                }
                            }"""
                            
                            element_handle = await target_page.evaluate_handle(js_get_element, element_selector)
                            if element_handle:
                                element = element_handle
                    except Exception as js_error:
                        error_message += f" JS定位尝试失败: {str(js_error)}"
            
            # 如果仍然找不到元素
            if not element:
                # 最后尝试直接通过JS进行点击操作
                try:
                    # 5. 直接使用JS执行点击操作
                    js_click_code = """(selector) => {
                        try {
                            const isXpath = selector.startsWith('/');
                            let element = null;
                            
                            if (isXpath) {
                                // XPath查询
                                const result = document.evaluate(
                                    selector, 
                                    document, 
                                    null, 
                                    XPathResult.FIRST_ORDERED_NODE_TYPE, 
                                    null
                                );
                                element = result.singleNodeValue;
                            } else {
                                // CSS查询
                                element = document.querySelector(selector);
                                
                                // 如果没找到，尝试简化选择器
                                if (!element && selector.includes('>')) {
                                    const simplified = selector.split('>').pop().trim();
                                    element = document.querySelector(simplified);
                                }
                                
                                // 如果仍未找到，尝试通过文本内容找到
                                if (!element && selector.includes(':nth-child')) {
                                    const baseSelector = selector.split(':nth-child')[0].trim();
                                    const elements = document.querySelectorAll(baseSelector);
                                    element = Array.from(elements)[0];
                                }
                            }
                            
                            if (element) {
                                // 高亮元素
                                const originalBackground = element.style.backgroundColor;
                                const originalOutline = element.style.outline;
                                
                                element.style.backgroundColor = 'rgba(255, 0, 0, 0.3)';
                                element.style.outline = '2px solid red';
                                element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                
                                // 执行点击
                                setTimeout(() => {
                                    element.style.backgroundColor = originalBackground;
                                    element.style.outline = originalOutline;
                                }, 1000);
                                
                                element.click();
                                return true;
                            }
                            return false;
                        } catch (error) {
                            console.error('点击元素出错:', error);
                            return false;
                        }
                    }"""
                    
                    click_success = await target_page.evaluate(js_click_code, element_selector)
                    
                    if click_success:
                        # 点击成功
                        if wait_for_navigation:
                            try:
                                # 等待导航或内容变化 (短超时，因为可能没有实际导航)
                                await target_page.wait_for_load_state('networkidle', timeout=2000)
                            except:
                                # 忽略等待导航的错误，因为可能没有实际导航
                                pass
                        
                        # 获取新标题和URL
                        new_title = await target_page.title()
                        new_url = target_page.url
                        
                        # 检测是否页面有变化 (但这不是唯一成功标准)
                        has_changes = (new_title != initial_title) or (new_url != initial_url)
                        
                        # 即使页面没有变化，我们也认为点击成功，只是在消息中提供额外信息
                        result['success'] = True
                        result['message'] = f"通过JavaScript成功点击元素" + (" (页面已更新)" if has_changes else "")
                        result['title'] = new_title
                        result['url'] = new_url
                        return result
                    
                    # JavaScript点击失败，但我们还有最后一招
                    # 尝试通过坐标点击
                    js_get_element_rect = """(selector) => {
                        // 尝试各种方法找到元素
                        let elements = [];
                        try {
                            if (selector.startsWith('/')) {
                                // XPath选择器
                                const result = document.evaluate(
                                    selector, document, null, 
                                    XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
                                );
                                for (let i = 0; i < result.snapshotLength; i++) {
                                    elements.push(result.snapshotItem(i));
                                }
                            } else {
                                // 基本CSS选择器
                                elements = Array.from(document.querySelectorAll(selector));
                                
                                // 如果没找到，尝试简化选择器
                                if (elements.length === 0 && selector.includes('>')) {
                                    const simplified = selector.split('>').pop().trim();
                                    elements = Array.from(document.querySelectorAll(simplified));
                                }
                                
                                // 如果仍未找到，尝试去掉:nth-child部分
                                if (elements.length === 0 && selector.includes(':nth-child')) {
                                    const baseSelector = selector.split(':nth-child')[0].trim();
                                    elements = Array.from(document.querySelectorAll(baseSelector));
                                }
                                
                                // 如果选择器包含类名，尝试只用类名
                                if (elements.length === 0 && selector.includes('.')) {
                                    const classes = selector.match(/\\.[a-zA-Z0-9_-]+/g);
                                    if (classes && classes.length > 0) {
                                        const classSelector = classes.join('');
                                        elements = Array.from(document.querySelectorAll(classSelector));
                                    }
                                }
                            }
                            
                            // 过滤掉不可见元素
                            elements = elements.filter(el => {
                                const style = window.getComputedStyle(el);
                                return style.display !== 'none' && 
                                       style.visibility !== 'hidden' && 
                                       style.opacity !== '0' &&
                                       el.offsetWidth > 0 &&
                                       el.offsetHeight > 0;
                            });
                            
                            if (elements.length > 0) {
                                const element = elements[0]; // 使用第一个匹配的元素
                                const rect = element.getBoundingClientRect();
                                
                                // 高亮元素
                                const originalBackground = element.style.backgroundColor;
                                const originalOutline = element.style.outline;
                                
                                element.style.backgroundColor = 'rgba(255, 0, 0, 0.3)';
                                element.style.outline = '2px solid red';
                                element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                
                                setTimeout(() => {
                                    element.style.backgroundColor = originalBackground;
                                    element.style.outline = originalOutline;
                                }, 1000);
                                
                                return {
                                    found: true,
                                    x: rect.left + rect.width / 2,
                                    y: rect.top + rect.height / 2,
                                    width: rect.width,
                                    height: rect.height
                                };
                            }
                        } catch (e) {
                            console.error('获取元素位置时出错:', e);
                        }
                        return { found: false };
                    }"""
                    
                    element_rect = await target_page.evaluate(js_get_element_rect, element_selector)
                    
                    if element_rect['found']:
                        # 通过坐标点击
                        x = element_rect['x']
                        y = element_rect['y']
                        
                        await target_page.mouse.click(x, y)
                        
                        if wait_for_navigation:
                            try:
                                # 等待导航或内容变化 (短超时)
                                await target_page.wait_for_load_state('networkidle', timeout=2000)
                            except:
                                # 忽略等待导航的错误
                                pass
                        
                        # 获取新标题和URL
                        new_title = await target_page.title()
                        new_url = target_page.url
                        
                        # 即使页面没有变化，也认为点击成功
                        result['success'] = True
                        result['message'] = f"通过坐标({x}, {y})成功点击元素"
                        result['title'] = new_title
                        result['url'] = new_url
                        return result
                except Exception as all_error:
                    error_message += f" 所有点击方法均失败: {str(all_error)}"
                
                # 如果所有尝试都失败了
                result['message'] = f"定位元素失败: {error_message}"
                return result
            
            # 如果成功找到元素，执行点击操作
            if click_type == 'click':
                try:
                    if wait_for_navigation:
                        try:
                            # 使用Promise.race等待点击或导航完成，较短的超时
                            async with target_page.expect_navigation(wait_until='domcontentloaded', timeout=5000):
                                await element.click()
                        except PlaywrightError as nav_error:
                            # 导航失败，但点击可能成功了
                            if "Navigation failed" in str(nav_error) or "Timeout" in str(nav_error):
                                # 我们认为点击本身成功了，无论页面是否有导航
                                result['success'] = True
                                result['message'] = "点击成功，无需页面导航"
                                result['title'] = await target_page.title()
                                result['url'] = target_page.url
                                return result
                            raise  # 重新抛出其他导航错误
                    else:
                        await element.click()
                except Exception as click_error:
                    # 尝试使用JavaScript点击作为后备方法
                    js_click = """(element) => { element.click(); return true; }"""
                    try:
                        click_success = await element.evaluate(js_click)
                        if click_success:
                            result['success'] = True
                            result['message'] = "通过JavaScript点击元素成功"
                            result['title'] = await target_page.title()
                            result['url'] = target_page.url
                            return result
                    except Exception:
                        # 如果JS点击也失败，重新抛出原始错误
                        raise click_error
                
            elif click_type == 'dblclick':
                await element.dblclick()
            elif click_type == 'hover':
                await element.hover()
            else:
                result['message'] = f"不支持的点击类型: {click_type}"
                return result
                
            # 等待页面加载完成
            if wait_for_navigation:
                try:
                    await target_page.wait_for_load_state('networkidle', timeout=2000)
                except:
                    # 忽略等待加载状态的错误
                    pass
            
            # 获取页面信息
            title = await target_page.title()
            current_url = target_page.url
            
            # 设置结果
            result['success'] = True
            result['message'] = f"成功{click_type}元素"
            result['title'] = title
            result['url'] = current_url
            
            return result
            
        except PlaywrightError as e:
            # 检查是否可能是导航失败但点击成功
            if "Navigation failed" in str(e) or "Timeout" in str(e):
                # 导航失败，但我们认为点击本身可能成功了
                result['success'] = True
                result['message'] = "点击操作成功，但无页面导航"
                try:
                    result['title'] = await target_page.title()
                    result['url'] = target_page.url
                except:
                    pass
                return result
                    
            if "Timeout" in str(e):
                result['message'] = f"等待元素超时: {element_selector}"
            else:
                result['message'] = f"点击元素时出错: {str(e)}"
            return result
            
        except Exception as e:
            result['message'] = f"点击元素时发生异常: {str(e)}"
            return result
    
    def click_element(self, page_index: int, element_selector: str, 
                    click_type: str = 'click', wait_for_navigation: bool = True) -> Dict[str, Any]:
        """
        点击指定元素
        
        Args:
            page_index: 页面序号（从0开始）
            element_selector: 元素选择器 (CSS或XPath)
            click_type: 点击类型 (click, dblclick, hover)
            wait_for_navigation: 是否等待页面导航完成
            
        Returns:
            点击操作结果
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': "未连接到浏览器，请先连接"
            }
        
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        try:
            return self._async_loop.run_until_complete(
                self._click_element_async(page_index, element_selector, click_type, wait_for_navigation)
            )
        except Exception as e:
            return {
                'success': False,
                'message': f"执行点击操作时出错: {str(e)}"
            }
    
    def _cleanup_sync(self):
        """同步清理资源 - 用于对象销毁时的安全清理"""
        try:
            # 标记为未连接
            self._is_connected = False
            
            # 清理引用，让垃圾收集器处理
            self.context = None
            self.page = None
            self.browser = None
            self.playwright = None
            
            # 注意：不在这里关闭事件循环，因为可能被其他地方使用
            # self._async_loop 保持不变，让其自然销毁
            
        except Exception as e:
            # 静默处理异常，避免在对象销毁时抛出异常
            pass
    
    def __del__(self):
        """析构函数，确保资源被释放 - 使用同步方法避免协程警告"""
        # 使用同步清理方法，避免协程未等待的警告
        if self._is_connected:
            self._cleanup_sync() 
    
    def long_screenshot_element(self, page_index: int, element_selector: str, 
                           output_path: str = None, step_size: int = 300) -> Dict[str, Any]:
        """
        对指定元素进行长截图，通过分步滚动并拼接截图实现
        支持主页面和iframe内的元素
        
        Args:
            page_index: 页面序号（从0开始）
            element_selector: 元素选择器 (CSS或XPath)
            output_path: 输出图片路径，如果为None则自动生成
            step_size: 每次滚动的像素大小，默认300
            
        Returns:
            包含操作结果的字典
        """
        import os
        from datetime import datetime
        import tempfile
        
        result = {
            'success': False,
            'message': '',
            'image_path': None
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        # 如果未提供输出路径，则生成一个
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"element_long_screenshot_{timestamp}.png"
        
        try:
            # 获取指定序号的页面
            pages = self.context.pages
            if page_index < 0 or page_index >= len(pages):
                result['message'] = f"无效的页面序号: {page_index}，有效范围: 0-{len(pages)-1}"
                return result
                
            target_page = pages[page_index]
            
            # 首先检查选择器是否在主页面中
            js_code_check = """(params) => {
                try {
                    const selector = params.selector;
                    const el = document.querySelector(selector);
                    return el ? true : false;
                } catch(e) {
                    return false;
                }
            }"""
            
            element_in_main_page = self._async_loop.run_until_complete(
                target_page.evaluate(js_code_check, {'selector': element_selector})
            )
            
            # 如果主页面中找不到元素，尝试在iframe中查找
            if not element_in_main_page:
                print(f"主页面中未找到元素，尝试在iframe中查找...")
                
                iframe_info = None
                content_frame = None
                iframe_handle = None
                
                # 获取所有iframe
                iframe_handles = self._async_loop.run_until_complete(
                    target_page.query_selector_all('iframe')
                )
                
                if not iframe_handles:
                    result['message'] = "在主页面和iframe中均未找到元素"
                    return result
                
                # 遍历iframe查找元素
                for i, handle in enumerate(iframe_handles):
                    frame = self._async_loop.run_until_complete(handle.content_frame())
                    if not frame:
                        continue
                        
                    # 在iframe中查找元素
                    element_in_frame = self._async_loop.run_until_complete(
                        frame.evaluate(js_code_check, {'selector': element_selector})
                    )
                    
                    if element_in_frame:
                        print(f"在iframe {i} 中找到元素")
                        iframe_info = {
                            'index': i,
                            'id': self._async_loop.run_until_complete(handle.get_attribute('id')) or f"iframe_{i}",
                            'name': self._async_loop.run_until_complete(handle.get_attribute('name')) or f"iframe_{i}",
                        }
                        content_frame = frame
                        iframe_handle = handle
                        break
                
                if not iframe_info:
                    result['message'] = "未在任何iframe中找到指定元素"
                    return result
                
                # 为在iframe中的元素进行长截图
                return self._long_screenshot_iframe_element(
                    target_page, content_frame, iframe_handle, element_selector, output_path, step_size
                )
            
            # 如果元素在主页面中，获取元素信息
            js_code = """(params) => {
                const selector = params.selector;
                const el = document.querySelector(selector);
                if (!el) return { found: false, message: '未找到元素' };
                
                // 获取元素的尺寸信息
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                
                return {
                    found: true,
                    scrollHeight: el.scrollHeight,
                    scrollWidth: el.scrollWidth,
                    clientHeight: el.clientHeight,
                    clientWidth: el.clientWidth,
                    rect: {
                        width: rect.width,
                        height: rect.height,
                        x: rect.x,
                        y: rect.y
                    },
                    hasScroll: el.scrollHeight > el.clientHeight
                };
            }"""
            
            element_info = self._async_loop.run_until_complete(
                target_page.evaluate(js_code, {'selector': element_selector})
            )
            
            if not element_info.get('found', False):
                result['message'] = element_info.get('message', '未找到元素')
                return result
            
            scroll_height = element_info.get('scrollHeight', 0)
            client_height = element_info.get('clientHeight', 0)
            has_scroll = element_info.get('hasScroll', False)
            
            if not has_scroll:
                # 如果元素没有滚动条，直接截图返回
                element_handle = self._async_loop.run_until_complete(
                    target_page.query_selector(element_selector)
                )
                if not element_handle:
                    result['message'] = "未找到元素"
                    return result
                
                self._async_loop.run_until_complete(
                    element_handle.screenshot(path=output_path)
                )
                result['success'] = True
                result['message'] = "成功截图（元素无需滚动）"
                result['image_path'] = output_path
                return result
            
            # 创建临时目录保存截图
            temp_dir = tempfile.mkdtemp()
            frame_paths = []
            
            # 计算需要截取的次数
            steps = max(1, int(scroll_height / step_size))
            
            # 首先滚动到元素顶部
            reset_scroll_js = """(params) => {
                const selector = params.selector;
                const el = document.querySelector(selector);
                if (el) {
                    el.scrollTo(0, 0);
                    return true;
                }
                return false;
            }"""
            
            scroll_reset = self._async_loop.run_until_complete(
                target_page.evaluate(reset_scroll_js, {'selector': element_selector})
            )
            
            if not scroll_reset:
                result['message'] = "无法重置元素滚动位置"
                return result
            
            # 分步截图
            for i in range(steps + 1):
                # 计算当前滚动位置
                current_scroll = i * step_size
                if current_scroll > scroll_height:
                    current_scroll = scroll_height
                
                # 滚动到指定位置
                scroll_js = """(params) => {
                    const selector = params.selector;
                    const scrollTop = params.scrollTop;
                    const el = document.querySelector(selector);
                    if (el) {
                        el.scrollTo(0, scrollTop);
                        return true;
                    }
                    return false;
                }"""
                
                scroll_success = self._async_loop.run_until_complete(
                    target_page.evaluate(scroll_js, {'selector': element_selector, 'scrollTop': current_scroll})
                )
                
                if not scroll_success:
                    result['message'] = f"滚动到位置 {current_scroll} 失败"
                    return result
                
                # 等待滚动完成
                self._async_loop.run_until_complete(asyncio.sleep(0.2))
                
                # 截取当前可见区域
                frame_path = os.path.join(temp_dir, f"frame_{i:03d}.png")
                element_handle = self._async_loop.run_until_complete(
                    target_page.query_selector(element_selector)
                )
                
                if not element_handle:
                    result['message'] = f"截图 {i+1}/{steps+1} 失败：无法获取元素"
                    return result
                
                self._async_loop.run_until_complete(
                    element_handle.screenshot(path=frame_path)
                )
                
                frame_paths.append(frame_path)
            
            # 拼接所有截图
            try:
                from PIL import Image
                
                # 获取第一张图片尺寸
                if not frame_paths:
                    result['message'] = "没有可用的截图帧"
                    return result
                    
                base_image = Image.open(frame_paths[0])
                width, height = base_image.size
                
                # 创建最终图像
                final_image = Image.new('RGB', (width, scroll_height), (255, 255, 255))
                
                # 拼接图片
                for i, frame_path in enumerate(frame_paths):
                    frame = Image.open(frame_path)
                    # 计算粘贴位置
                    y_position = min(i * step_size, scroll_height - height)
                    
                    # 如果是最后一帧，可能需要特殊处理，避免超出总高度
                    if i == len(frame_paths) - 1:
                        # 计算最后一帧应该显示的部分高度
                        visible_height = scroll_height - y_position
                        if visible_height < height:
                            # 裁剪最后一帧
                            frame = frame.crop((0, 0, width, visible_height))
                    
                    final_image.paste(frame, (0, y_position))
                
                # 保存最终图像
                final_image.save(output_path)
                
                # 清理临时文件
                for frame_path in frame_paths:
                    try:
                        os.remove(frame_path)
                    except:
                        pass
                try:
                    os.rmdir(temp_dir)
                except:
                    pass
                
                result['success'] = True
                result['message'] = f"成功创建长截图，包含 {len(frame_paths)} 个片段"
                result['image_path'] = output_path
                
                return result
                
            except ImportError:
                result['message'] = "无法导入PIL库，请先安装：pip install pillow"
                return result
            except Exception as e:
                result['message'] = f"拼接图片时出错: {str(e)}"
                return result
                
        except Exception as e:
            result['message'] = f"长截图过程中出错: {str(e)}"
            return result
            
    def _long_screenshot_iframe_element(self, page, frame, iframe_handle, element_selector, output_path, step_size):
        """
        对iframe内的元素进行长截图
        
        Args:
            page: 主页面对象
            frame: iframe内容框架对象
            iframe_handle: iframe元素句柄
            element_selector: 元素选择器
            output_path: 输出路径
            step_size: 滚动步长
            
        Returns:
            操作结果字典
        """
        import os
        import tempfile
        
        result = {
            'success': False,
            'message': '',
            'image_path': None
        }
        
        try:
            # 获取iframe内元素的信息
            js_code = """(params) => {
                const selector = params.selector;
                const el = document.querySelector(selector);
                if (!el) return { found: false, message: '未找到元素' };
                
                // 获取元素的尺寸信息
                const rect = el.getBoundingClientRect();
                
                return {
                    found: true,
                    scrollHeight: el.scrollHeight,
                    scrollWidth: el.scrollWidth,
                    clientHeight: el.clientHeight,
                    clientWidth: el.clientWidth,
                    rect: {
                        width: rect.width,
                        height: rect.height,
                        x: rect.x,
                        y: rect.y
                    },
                    hasScroll: el.scrollHeight > el.clientHeight
                };
            }"""
            
            element_info = self._async_loop.run_until_complete(
                frame.evaluate(js_code, {'selector': element_selector})
            )
            
            if not element_info.get('found', False):
                result['message'] = element_info.get('message', '在iframe中未找到元素')
                return result
            
            scroll_height = element_info.get('scrollHeight', 0)
            client_height = element_info.get('clientHeight', 0)
            has_scroll = element_info.get('hasScroll', False)
            
            # 获取iframe位置信息
            iframe_rect = self._async_loop.run_until_complete(iframe_handle.bounding_box())
            if not iframe_rect:
                result['message'] = "无法获取iframe位置"
                return result
                
            print(f"iframe位置: x={iframe_rect['x']}, y={iframe_rect['y']}, 宽={iframe_rect['width']}, 高={iframe_rect['height']}")
            print(f"元素滚动高度: {scroll_height}, 可见高度: {client_height}, 需要滚动: {has_scroll}")
            
            if not has_scroll:
                # 如果元素没有滚动条，直接截图返回
                element_handle = self._async_loop.run_until_complete(
                    frame.query_selector(element_selector)
                )
                if not element_handle:
                    result['message'] = "在iframe中未找到元素"
                    return result
                
                self._async_loop.run_until_complete(
                    element_handle.screenshot(path=output_path)
                )
                result['success'] = True
                result['message'] = "成功截图iframe内元素（无需滚动）"
                result['image_path'] = output_path
                return result
            
            # 创建临时目录保存截图
            temp_dir = tempfile.mkdtemp()
            frame_paths = []
            
            # 计算需要截取的次数
            steps = max(1, int(scroll_height / step_size))
            
            # 首先滚动到元素顶部
            reset_scroll_js = """(params) => {
                const selector = params.selector;
                const el = document.querySelector(selector);
                if (el) {
                    el.scrollTo(0, 0);
                    return true;
                }
                return false;
            }"""
            
            scroll_reset = self._async_loop.run_until_complete(
                frame.evaluate(reset_scroll_js, {'selector': element_selector})
            )
            
            if not scroll_reset:
                result['message'] = "无法重置iframe内元素滚动位置"
                return result
            
            # 首先确保iframe可见
            scroll_iframe_js = """(params) => {
                const selector = params.selector;
                const iframe = document.querySelector(selector);
                if (iframe) {
                    iframe.scrollIntoView({behavior: 'auto', block: 'start'});
                    return true;
                }
                return false;
            }"""
            
            # 构建iframe选择器（简单情况下使用iframe索引）
            iframe_selector = f"iframe:nth-of-type({element_info.get('index', 1) + 1})"
            
            self._async_loop.run_until_complete(
                page.evaluate(scroll_iframe_js, {'selector': iframe_selector})
            )
            
            # 分步截图
            for i in range(steps + 1):
                # 计算当前滚动位置
                current_scroll = i * step_size
                if current_scroll > scroll_height:
                    current_scroll = scroll_height
                
                # 滚动到指定位置
                scroll_js = """(params) => {
                    const selector = params.selector;
                    const scrollTop = params.scrollTop;
                    const el = document.querySelector(selector);
                    if (el) {
                        el.scrollTo(0, scrollTop);
                        return true;
                    }
                    return false;
                }"""
                
                scroll_success = self._async_loop.run_until_complete(
                    frame.evaluate(scroll_js, {'selector': element_selector, 'scrollTop': current_scroll})
                )
                
                if not scroll_success:
                    result['message'] = f"滚动iframe内元素到位置 {current_scroll} 失败"
                    return result
                
                # 等待滚动完成
                self._async_loop.run_until_complete(asyncio.sleep(0.3))
                
                # 截取当前可见区域
                frame_path = os.path.join(temp_dir, f"frame_{i:03d}.png")
                element_handle = self._async_loop.run_until_complete(
                    frame.query_selector(element_selector)
                )
                
                if not element_handle:
                    result['message'] = f"截图iframe内元素 {i+1}/{steps+1} 失败：无法获取元素"
                    return result
                
                self._async_loop.run_until_complete(
                    element_handle.screenshot(path=frame_path)
                )
                
                frame_paths.append(frame_path)
            
            # 拼接所有截图
            try:
                from PIL import Image
                
                # 获取第一张图片尺寸
                if not frame_paths:
                    result['message'] = "没有可用的截图帧"
                    return result
                    
                base_image = Image.open(frame_paths[0])
                width, height = base_image.size
                
                # 创建最终图像
                final_image = Image.new('RGB', (width, scroll_height), (255, 255, 255))
                
                # 拼接图片
                for i, frame_path in enumerate(frame_paths):
                    frame = Image.open(frame_path)
                    # 计算粘贴位置
                    y_position = min(i * step_size, scroll_height - height)
                    
                    # 如果是最后一帧，可能需要特殊处理，避免超出总高度
                    if i == len(frame_paths) - 1:
                        # 计算最后一帧应该显示的部分高度
                        visible_height = scroll_height - y_position
                        if visible_height < height:
                            # 裁剪最后一帧
                            frame = frame.crop((0, 0, width, visible_height))
                    
                    final_image.paste(frame, (0, y_position))
                
                # 保存最终图像
                final_image.save(output_path)
                
                # 清理临时文件
                for frame_path in frame_paths:
                    try:
                        os.remove(frame_path)
                    except:
                        pass
                try:
                    os.rmdir(temp_dir)
                except:
                    pass
                
                result['success'] = True
                result['message'] = f"成功创建iframe内元素的长截图，包含 {len(frame_paths)} 个片段"
                result['image_path'] = output_path
                
                return result
                
            except ImportError:
                result['message'] = "无法导入PIL库，请先安装：pip install pillow"
                return result
            except Exception as e:
                result['message'] = f"拼接iframe内元素截图时出错: {str(e)}"
                return result
                
        except Exception as e:
            result['message'] = f"iframe内元素长截图过程中出错: {str(e)}"
            return result
    
    def execute_javascript(self, page_index: int, javascript_code: str) -> Dict[str, Any]:
        """
        在指定页面执行JavaScript代码
        
        Args:
            page_index: 页面索引
            javascript_code: 要执行的JavaScript代码
            
        Returns:
            执行结果
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': '浏览器未连接'
            }
        
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        try:
            return self._async_loop.run_until_complete(
                self._execute_javascript_async(page_index, javascript_code)
            )
        except Exception as e:
            return {
                'success': False,
                'message': f'执行JavaScript时出错: {str(e)}'
            }
    
    async def _execute_javascript_async(self, page_index: int, javascript_code: str) -> Dict[str, Any]:
        """
        异步在指定页面执行JavaScript代码
        
        Args:
            page_index: 页面索引
            javascript_code: 要执行的JavaScript代码
            
        Returns:
            执行结果
        """
        result = {
            'success': False,
            'message': '',
            'result': None
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器"
            return result
        
        if not self.context:
            result['message'] = "无法获取浏览器上下文"
            return result
            
        # 获取所有页面
        pages = self.context.pages
        
        # 检查页面索引是否有效
        if page_index < 0 or page_index >= len(pages):
            result['message'] = f"无效的页面索引: {page_index}，有效范围: 0-{len(pages)-1}"
            return result
        
        try:
            # 获取目标页面
            target_page = pages[page_index]
            
            # 执行JavaScript代码
            js_result = await target_page.evaluate(javascript_code)
            
            result['success'] = True
            result['message'] = "JavaScript执行成功"
            result['result'] = js_result
            
            return result
            
        except Exception as e:
            result['message'] = f"执行JavaScript时出错: {str(e)}"
            return result
    
    async def _get_navigation_target_url_async(self, page_index: int, action_callback, timeout: int = 10000) -> Dict[str, Any]:
        """
        执行操作并监听导航事件，获取目标URL
        
        Args:
            page_index: 页面索引
            action_callback: 要执行的操作（如点击按钮）的回调函数
            timeout: 超时时间（毫秒）
            
        Returns:
            包含目标URL的结果
        """
        result = {
            'success': False,
            'message': '',
            'target_url': None,
            'final_url': None,
            'navigation_history': []
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器"
            return result
        
        if not self.context:
            result['message'] = "无法获取浏览器上下文"
            return result
            
        # 获取所有页面
        pages = self.context.pages
        
        # 检查页面索引是否有效
        if page_index < 0 or page_index >= len(pages):
            result['message'] = f"无效的页面索引: {page_index}，有效范围: 0-{len(pages)-1}"
            return result
        
        try:
            # 获取目标页面
            target_page = pages[page_index]
            
            # 用于存储导航历史
            navigation_urls = []
            target_url = None
            
            # 定义事件处理器
            def handle_request(request):
                """处理导航请求事件"""
                try:
                    url = request.url
                    print(f"[请求事件] URL: {url}, 导航请求: {request.is_navigation_request()}")
                    
                    if request.is_navigation_request() and request.frame == target_page.main_frame:
                        if url.startswith("http://") or url.startswith("https://"):
                            navigation_urls.append({
                                'type': 'request',
                                'url': url,
                                'time': time.time()
                            })
                            nonlocal target_url
                            target_url = url
                            print(f"[导航请求] 浏览器尝试导航到: {url}")
                except Exception as e:
                    print(f"[错误] 处理请求事件时出错: {str(e)}")
            
            def handle_frame_navigated(frame):
                """处理框架导航完成事件"""
                try:
                    url = frame.url
                    print(f"[框架导航] URL: {url}, 是主框架: {frame.parent_frame is None}")
                    
                    if frame.parent_frame is None:  # 主框架
                        navigation_urls.append({
                            'type': 'navigated',
                            'url': url,
                            'time': time.time()
                        })
                        print(f"[导航完成] 框架实际导航到: {url}")
                        # 如果是有效URL，更新target_url
                        if url.startswith("http://") or url.startswith("https://"):
                            nonlocal target_url
                            target_url = url
                except Exception as e:
                    print(f"[错误] 处理框架导航事件时出错: {str(e)}")
            
            def handle_response(response):
                """处理响应事件"""
                try:
                    url = response.url
                    status = response.status
                    print(f"[响应事件] URL: {url}, 状态: {status}")
                    
                    # 如果是3xx重定向响应，记录目标URL
                    if 300 <= status < 400:
                        headers = response.headers
                        location = headers.get('location', '')
                        if location:
                            print(f"[重定向] 从 {url} 重定向到 {location}")
                            navigation_urls.append({
                                'type': 'redirect',
                                'from': url,
                                'to': location,
                                'time': time.time()
                            })
                except Exception as e:
                    print(f"[错误] 处理响应事件时出错: {str(e)}")
            
            # 注册事件监听器
            target_page.on("request", handle_request)
            target_page.on("framenavigated", handle_frame_navigated)
            target_page.on("response", handle_response)
            
            # 记录初始URL
            initial_url = target_page.url
            print(f"[初始] 页面URL: {initial_url}")
            
            try:
                # 执行操作（如点击按钮）
                if callable(action_callback):
                    await action_callback(target_page)
                
                # 等待一段时间，让导航事件有机会触发
                print("[等待] 等待导航事件...")
                await asyncio.sleep(2)
                
                # 检查是否有新页面打开
                current_pages = self.context.pages
                if len(current_pages) > len(pages):
                    print(f"[新页面] 检测到新页面打开，当前页面数: {len(current_pages)}")
                    # 获取新页面的URL
                    for i, page in enumerate(current_pages):
                        if page not in pages:
                            new_url = page.url
                            new_title = await page.title()
                            print(f"[新页面] 索引 {i}: {new_title} ({new_url})")
                            if new_url.startswith("http://") or new_url.startswith("https://"):
                                target_url = new_url
                                navigation_urls.append({
                                    'type': 'new_page',
                                    'url': new_url,
                                    'time': time.time()
                                })
                
                # 等待导航完成或超时
                try:
                    await target_page.wait_for_load_state('networkidle', timeout=timeout-2000)
                except:
                    # 即使超时也继续，因为我们可能已经捕获到了目标URL
                    print("[超时] 等待页面加载超时，继续处理...")
                
                # 获取最终URL
                final_url = target_page.url
                print(f"[最终] 页面URL: {final_url}")
                
                # 如果URL没有变化，可能是JavaScript导航
                if final_url == initial_url and not target_url:
                    print("[检查] URL未变化，尝试获取JavaScript导航信息...")
                    # 尝试通过JavaScript获取可能的导航信息
                    js_result = await target_page.evaluate("""
                        () => {
                            // 检查是否有window.location的变化
                            const info = {
                                href: window.location.href,
                                // 检查是否有计划的导航
                                pendingNavigation: window.location.href
                            };
                            
                            // 检查是否有meta refresh
                            const metaRefresh = document.querySelector('meta[http-equiv="refresh"]');
                            if (metaRefresh) {
                                info.metaRefresh = metaRefresh.getAttribute('content');
                            }
                            
                            return info;
                        }
                    """)
                    print(f"[JavaScript] 页面信息: {js_result}")
                
                result['success'] = True
                result['target_url'] = target_url
                result['final_url'] = final_url
                result['navigation_history'] = navigation_urls
                
                # 判断是否导航到了错误页面
                if final_url.startswith("chrome-error://"):
                    result['message'] = f"导航到错误页面，目标URL是: {target_url}"
                elif target_url:
                    result['message'] = f"捕获到目标URL: {target_url}"
                else:
                    result['message'] = "未捕获到导航事件"
                
            finally:
                # 移除事件监听器
                target_page.remove_listener("request", handle_request)
                target_page.remove_listener("framenavigated", handle_frame_navigated)
                target_page.remove_listener("response", handle_response)
            
            return result
            
        except Exception as e:
            result['message'] = f"监听导航事件时出错: {str(e)}"
            import traceback
            traceback.print_exc()
            return result
    
    def get_navigation_target_url(self, page_index: int, action_callback, timeout: int = 10000) -> Dict[str, Any]:
        """
        执行操作并监听导航事件，获取目标URL
        
        Args:
            page_index: 页面索引
            action_callback: 要执行的操作（如点击按钮）的回调函数
            timeout: 超时时间（毫秒）
            
        Returns:
            包含目标URL的结果
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': '浏览器未连接'
            }
        
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        try:
            return self._async_loop.run_until_complete(
                self._get_navigation_target_url_async(page_index, action_callback, timeout)
            )
        except Exception as e:
            return {
                'success': False,
                'message': f'执行导航监听时出错: {str(e)}'
            }
    
    def create_new_tab_background(self, url: str = 'about:blank') -> Dict[str, Any]:
        """
        在后台创建新的标签页（不切换焦点）
        
        Args:
            url: 新标签页的URL，默认为空白页
            
        Returns:
            创建结果信息
        """
        if not self._is_connected:
            return {
                'success': False,
                'message': "未连接到浏览器，请先连接"
            }
        
        if not self._async_loop:
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
        
        try:
            return self._async_loop.run_until_complete(
                self._create_new_tab_background_async(url)
            )
        except Exception as e:
            return {
                'success': False,
                'message': f"执行创建新标签页时出错: {str(e)}"
            }
    
    async def _create_new_tab_background_async(self, url: str = 'about:blank') -> Dict[str, Any]:
        """
        异步在后台创建新的标签页（不切换焦点）
        
        Args:
            url: 新标签页的URL，默认为空白页
            
        Returns:
            创建结果信息
        """
        result = {
            'success': False,
            'message': '',
            'page_index': -1,
            'title': None,
            'url': None
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        if not self.context:
            result['message'] = "无法获取浏览器上下文"
            return result
        
        try:
            # 保存当前页面引用
            current_page = self.page
            
            # 创建新的页面
            new_page = await self.context.new_page()
            
            # 导航到指定URL
            await new_page.goto(url, wait_until='domcontentloaded')
            
            # 等待页面加载
            await new_page.wait_for_load_state('networkidle')
            
            # 获取页面信息
            title = await new_page.title()
            current_url = new_page.url
            
            # 获取页面序号
            pages = self.context.pages
            page_index = next((i for i, p in enumerate(pages) if p == new_page), -1)
            
            # 重要：不切换到新页面，保持原页面的焦点
            # self.page = new_page  # 注释掉这行
            
            # 如果有原页面，将焦点切回原页面
            if current_page and not current_page.is_closed():
                await current_page.bring_to_front()
            
            # 设置结果
            result['success'] = True
            result['message'] = f"成功在后台创建新标签页: {title}"
            result['page_index'] = page_index
            result['title'] = title
            result['url'] = current_url
            
            return result
            
        except PlaywrightError as e:
            result['message'] = f"创建新标签页时出错: {str(e)}"
            return result
            
        except Exception as e:
            result['message'] = f"创建新标签页时发生异常: {str(e)}"
            return result
    
    async def _navigate_page_async(self, page_index: int, url: str) -> Dict[str, Any]:
        """
        异步让指定序号的页面导航到URL
        
        Args:
            page_index: 页面序号（从0开始）
            url: 要导航到的URL
            
        Returns:
            导航结果信息
        """
        result = {
            'success': False,
            'message': '',
            'title': None,
            'url': None,
            'status': None
        }
        
        if not self._is_connected:
            result['message'] = "未连接到浏览器，请先连接"
            return result
        
        if not self.context:
            result['message'] = "无法获取浏览器上下文"
            return result
            
        # 获取所有页面
        pages = self.context.pages
        
        # 检查页面序号是否有效
        if page_index < 0 or page_index >= len(pages):
            result['message'] = f"无效的页面序号: {page_index}，有效范围: 0-{len(pages)-1}"
            return result
        
        try:
            # 获取指定序号的页面
            target_page = pages[page_index]
            
            # 导航到指定URL
            response = await target_page.goto(url, wait_until='domcontentloaded')
            
            # 等待页面加载
            await target_page.wait_for_load_state('networkidle')
            
            # 获取页面信息
            title = await target_page.title()
            current_url = target_page.url
            
            # 设置结果
            result['success'] = True
            result['message'] = f"成功将页面 {page_index} 导航到: {title}"
            result['title'] = title
            result['url'] = current_url
            result['status'] = response.status if response else None
            
            return result
            
        except PlaywrightError as e:
            result['message'] = f"导航页面 {page_index} 时出错: {str(e)}"
            return result
            
        except Exception as e:
            result['message'] = f"导航页面 {page_index} 时发生异常: {str(e)}"
            return result