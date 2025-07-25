import os
import sys
import time
import pathlib
import json
import re
import tempfile
import xml.dom.minidom
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Union, Tuple
from ppadb.client import Client as AdbClient

# 处理导入路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))


class PPADBTool:
    """Android设备自动化工具类，封装ADB相关的操作接口"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 5037, device_serial: Optional[str] = None):
        """
        初始化PPADB工具
        
        Args:
            host: ADB服务器主机，默认为本地
            port: ADB服务器端口，默认为5037
            device_serial: 设备序列号，如果提供则直接连接该设备，否则连接第一个可用设备
        """
        self.host = host
        self.port = port
        self.client = AdbClient(host=host, port=port)
        self.device = None
        self.device_serial = device_serial
        
        # 尝试连接设备
        if device_serial:
            # 连接指定序列号的设备
            self.select_device(device_serial)
        else:
            # 尝试连接第一个可用设备
            self._connect_first_device()
    
    def _connect_first_device(self) -> bool:
        """
        连接第一个可用设备
        
        Returns:
            是否成功连接设备
        """
        devices_result = self.get_devices()
        if not devices_result['success'] or not devices_result['devices']:
            print("未找到可用设备")
            return False
        
        # 选择第一个设备
        first_device = devices_result['devices'][0]
        return self.select_device(first_device['serial'])
    
    def get_devices(self) -> Dict[str, Any]:
        """
        获取所有连接的设备
        
        Returns:
            设备列表信息，格式为：
            {
                'success': bool,
                'message': str,
                'devices': [
                    {
                        'serial': str,
                        'state': str,
                        'properties': {
                            'model': str,
                            'version': str,
                            'device': str,
                            ...其他属性
                        }
                    },
                    ...更多设备
                ]
            }
        """
        result = {
            'success': False,
            'message': '',
            'devices': []
        }
        
        try:
            devices = self.client.devices()
            device_list = []
            
            for device in devices:
                try:
                    # 基本信息
                    device_info = {
                        'serial': device.serial,
                        'state': device.get_state(),
                        'properties': {}
                    }
                    
                    # 尝试获取设备属性
                    try:
                        props = device.get_properties()
                        device_info['properties'] = {
                            'model': props.get('ro.product.model', 'Unknown'),
                            'brand': props.get('ro.product.brand', 'Unknown'),
                            'manufacturer': props.get('ro.product.manufacturer', 'Unknown'),
                            'version': props.get('ro.build.version.release', 'Unknown'),
                            'sdk': props.get('ro.build.version.sdk', 'Unknown'),
                            'device': props.get('ro.product.device', 'Unknown')
                        }
                    except Exception as prop_error:
                        print(f"获取设备属性时出错: {prop_error}")
                        # 属性获取失败不影响整体结果，继续处理下一步
                    
                    device_list.append(device_info)
                except Exception as device_error:
                    print(f"处理设备 {device.serial} 时出错: {device_error}")
                    # 单个设备处理失败不影响其他设备，继续处理下一个
            
            result['success'] = True
            result['message'] = f"找到 {len(device_list)} 个设备"
            result['devices'] = device_list
            
            return result
            
        except Exception as e:
            result['message'] = f"获取设备列表失败: {str(e)}"
            return result
    
    def select_device(self, device_serial: str) -> bool:
        """
        选择并连接指定的设备
        
        Args:
            device_serial: 设备序列号
            
        Returns:
            是否成功连接设备
        """
        try:
            device = self.client.device(device_serial)
            if device:
                self.device = device
                self.device_serial = device_serial
                print(f"已连接设备: {device_serial}")
                return True
            else:
                print(f"找不到序列号为 {device_serial} 的设备")
                return False
        except Exception as e:
            print(f"连接设备 {device_serial} 失败: {str(e)}")
            return False
    
    def get_current_device(self) -> Dict[str, Any]:
        """
        获取当前连接的设备信息
        
        Returns:
            当前设备信息，格式为：
            {
                'success': bool,
                'message': str,
                'device': {
                    'serial': str,
                    'state': str,
                    'properties': {
                        'model': str,
                        'version': str,
                        ...其他属性
                    }
                }
            }
        """
        result = {
            'success': False,
            'message': '',
            'device': None
        }
        
        if not self.device:
            result['message'] = "未连接设备"
            return result
            
        try:
            # 获取设备状态和属性
            device_info = {
                'serial': self.device.serial,
                'state': self.device.get_state(),
                'properties': {}
            }
            
            # 尝试获取设备属性
            try:
                props = self.device.get_properties()
                device_info['properties'] = {
                    'model': props.get('ro.product.model', 'Unknown'),
                    'brand': props.get('ro.product.brand', 'Unknown'),
                    'manufacturer': props.get('ro.product.manufacturer', 'Unknown'),
                    'version': props.get('ro.build.version.release', 'Unknown'),
                    'sdk': props.get('ro.build.version.sdk', 'Unknown'),
                    'device': props.get('ro.product.device', 'Unknown')
                }
            except Exception as prop_error:
                print(f"获取设备属性时出错: {prop_error}")
            
            result['success'] = True
            result['message'] = f"已连接设备: {self.device.serial}"
            result['device'] = device_info
            
            return result
            
        except Exception as e:
            result['message'] = f"获取当前设备信息失败: {str(e)}"
            return result
    
    def is_device_connected(self) -> bool:
        """
        检查设备是否已连接
        
        Returns:
            设备是否已连接
        """
        return self.device is not None
    
    def disconnect(self) -> Dict[str, Any]:
        """
        断开当前设备连接
        
        Returns:
            断开连接结果
        """
        result = {
            'success': False,
            'message': ''
        }
        
        if not self.device:
            result['message'] = "当前未连接设备"
            return result
            
        try:
            serial = self.device.serial
            self.device = None
            self.device_serial = None
            
            result['success'] = True
            result['message'] = f"已断开设备 {serial} 的连接"
            return result
        except Exception as e:
            result['message'] = f"断开设备连接时出错: {str(e)}"
            return result
    
    def get_screen_size(self) -> Dict[str, Any]:
        """
        获取设备屏幕尺寸
        
        Returns:
            屏幕尺寸信息，格式为：
            {
                'success': bool,
                'message': str,
                'width': int,    # 屏幕宽度（像素）
                'height': int,   # 屏幕高度（像素）
            }
        """
        result = {
            'success': False,
            'message': '',
            'width': 0,
            'height': 0
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 使用dumpsys window命令获取屏幕尺寸
            output = self.device.shell('dumpsys window displays')
            
            # 解析输出中的屏幕尺寸信息
            # 寻找类似 "init=1080x2340"或"cur=1080x2340"的字符串
            size_pattern = r'(\w+)=(\d+)x(\d+)'
            matches = re.findall(size_pattern, output)
            
            if matches:
                # 优先使用cur或real尺寸，其次使用init尺寸
                size_dict = {match[0]: (int(match[1]), int(match[2])) for match in matches}
                
                if 'cur' in size_dict:
                    width, height = size_dict['cur']
                elif 'real' in size_dict:
                    width, height = size_dict['real']
                elif 'init' in size_dict:
                    width, height = size_dict['init']
                else:
                    # 使用找到的第一个尺寸
                    width, height = size_dict[list(size_dict.keys())[0]]
                
                result['success'] = True
                result['message'] = f'获取屏幕尺寸成功: {width}x{height}'
                result['width'] = width
                result['height'] = height
            else:
                # 尝试使用wm size命令作为备选方案
                output = self.device.shell('wm size')
                match = re.search(r'Physical size: (\d+)x(\d+)', output)
                
                if match:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    
                    result['success'] = True
                    result['message'] = f'获取屏幕尺寸成功: {width}x{height}'
                    result['width'] = width
                    result['height'] = height
                else:
                    result['message'] = '无法解析屏幕尺寸信息'
            
            return result
            
        except Exception as e:
            result['message'] = f'获取屏幕尺寸时出错: {str(e)}'
            return result

    def get_installed_packages(self, filter_type: str = "all") -> Dict[str, Any]:
        """
        获取设备已安装的应用包列表
        
        Args:
            filter_type: 过滤类型，可选值: "all"(所有应用), "system"(系统应用), "3rd"(第三方应用)
            
        Returns:
            包含应用包名列表的结果，格式为：
            {
                'success': bool,
                'message': str,
                'packages': [
                    {
                        'package_name': str,  # 包名
                        'app_name': str,      # 应用名称（如果能获取到）
                        'system': bool,       # 是否是系统应用
                        'path': str           # 应用安装路径
                    },
                    ...更多应用
                ]
            }
        """
        result = {
            'success': False,
            'message': '',
            'packages': []
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 根据过滤类型构建命令
            if filter_type == "system":
                cmd = 'pm list packages -s'  # 只列出系统应用
            elif filter_type == "3rd":
                cmd = 'pm list packages -3'  # 只列出第三方应用
            else:
                cmd = 'pm list packages'     # 列出所有应用
            
            # 获取包列表
            output = self.device.shell(cmd)
            if not output:
                result['message'] = '未能获取应用列表'
                return result
                
            # 解析输出，格式为"package:com.example.app"
            package_names = [line.split(':', 1)[1].strip() for line in output.splitlines() if ':' in line]
            
            # 获取每个包的详细信息
            packages_info = []
            for package_name in package_names:
                try:
                    # 获取应用路径
                    path_output = self.device.shell(f'pm path {package_name}')
                    path = path_output.split(':', 1)[1].strip() if ':' in path_output else ''
                    
                    # 判断是否为系统应用
                    is_system = path.startswith('/system/') if path else False
                    
                    # 尝试获取应用名称
                    app_name = package_name
                    try:
                        # 这里使用dumpsys获取应用标签，但可能不是所有设备都支持
                        label_output = self.device.shell(f'dumpsys package {package_name} | grep "labelRes"')
                        if label_output:
                            # 实际情况中这种方式可能不准确，可能需要其他方法
                            app_name = label_output.strip()
                    except:
                        pass
                    
                    # 添加到结果列表
                    packages_info.append({
                        'package_name': package_name,
                        'app_name': app_name,
                        'system': is_system,
                        'path': path
                    })
                except Exception as package_error:
                    print(f"获取应用 {package_name} 详情时出错: {package_error}")
                    # 错误不影响其他应用的处理
                    packages_info.append({
                        'package_name': package_name,
                        'app_name': package_name,
                        'system': False,
                        'path': ''
                    })
            
            # 更新结果
            result['success'] = True
            result['message'] = f'找到 {len(packages_info)} 个应用'
            result['packages'] = packages_info
            
            return result
            
        except Exception as e:
            result['message'] = f'获取应用列表出错: {str(e)}'
            return result
    
    def launch_app(self, package_name: str, activity_name: Optional[str] = None) -> Dict[str, Any]:
        """
        启动应用
        
        Args:
            package_name: 应用包名，例如'com.android.settings'
            activity_name: 活动名称，如果提供则使用am start启动特定活动，否则使用monkey启动应用
            
        Returns:
            操作结果，格式为：
            {
                'success': bool,
                'message': str,
                'output': str  # 命令输出
            }
        """
        result = {
            'success': False,
            'message': '',
            'output': ''
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 使用不同方法启动应用
            if activity_name:
                # 使用am命令启动特定活动
                cmd = f'am start -n {package_name}/{activity_name}'
                output = self.device.shell(cmd)
                success = 'Starting:' in output and 'Error' not in output
            else:
                # 使用monkey命令启动应用
                cmd = f'monkey -p {package_name} -c android.intent.category.LAUNCHER 1'
                output = self.device.shell(cmd)
                success = 'Events injected' in output
            
            # 设置结果
            result['success'] = success
            result['output'] = output
            
            if success:
                result['message'] = f'成功启动应用 {package_name}'
            else:
                result['message'] = f'启动应用 {package_name} 失败'
            
            return result
            
        except Exception as e:
            result['message'] = f'启动应用出错: {str(e)}'
            return result
    
    def get_current_app_ui(self, pretty_print: bool = True, save_xml: bool = False, 
                        save_path: Optional[str] = None, max_depth: int = 50) -> Dict[str, Any]:
        """
        获取当前应用的UI结构（默认递归获取完整UI树）
        
        Args:
            pretty_print: 是否美化XML输出，默认为True
            save_xml: 是否保存XML到文件，默认为False
            save_path: 保存XML的路径，如果为None则使用临时目录
            max_depth: 递归解析的最大深度，默认为50层（通常足够分析大多数应用）
            
        Returns:
            UI结构信息，格式为：
            {
                'success': bool,
                'message': str,
                'package_name': str,       # 当前应用包名
                'activity_name': str,      # 当前应用活动名称
                'xml': str,                # UI层次结构的XML
                'xml_file_path': str,      # 如果save_xml为True，保存的XML文件路径
                'elements': [              # 界面元素列表
                    {
                        'class': str,         # 元素类名
                        'resource-id': str,   # 资源ID
                        'text': str,          # 文本内容
                        'content-desc': str,  # 内容描述
                        'bounds': [x1,y1,x2,y2], # 边界坐标
                        'clickable': bool,    # 是否可点击
                        'long-clickable': bool, # 是否可长按
                        'checkable': bool,    # 是否可选中
                        'checked': bool,      # 是否已选中
                        'enabled': bool,      # 是否启用
                        'focusable': bool,    # 是否可获取焦点
                        'focused': bool,      # 是否已获取焦点
                        'password': bool,     # 是否密码字段
                        'scrollable': bool,   # 是否可滚动
                        'depth': int,         # 元素在层次结构中的深度
                        'parent_index': int,  # 父元素在列表中的索引（如果有）
                        'child_indices': [int], # 子元素在列表中的索引列表
                    },
                    ...更多元素
                ]
            }
        """
        result = {
            'success': False,
            'message': '',
            'package_name': '',
            'activity_name': '',
            'xml': '',
            'xml_file_path': '',
            'elements': []
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 获取当前应用信息
            current_app_cmd = 'dumpsys window | grep -E "mCurrentFocus|mFocusedApp"'
            current_app_output = self.device.shell(current_app_cmd)
            
            # 解析包名和活动名
            package_pattern = r'(\S+)/(\S+)'
            matches = re.findall(package_pattern, current_app_output)
            
            if matches:
                package_name, activity_name = matches[0]
                result['package_name'] = package_name
                result['activity_name'] = activity_name
            else:
                # 尝试其他提取方式
                alt_pattern = r'(\S+)\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)'
                alt_matches = re.findall(alt_pattern, current_app_output)
                if alt_matches:
                    result['package_name'] = alt_matches[0][0]
                    result['activity_name'] = alt_matches[0][1]
                else:
                    result['message'] = '无法获取当前应用信息'
                    return result
            
            # 使用UI Automator获取界面层次结构
            # 创建一个临时文件路径用于保存UI XML
            if save_xml and save_path:
                xml_temp_path = save_path
                if not os.path.exists(os.path.dirname(xml_temp_path)):
                    os.makedirs(os.path.dirname(xml_temp_path))
            else:
                temp_dir = tempfile.gettempdir()
                xml_temp_path = os.path.join(temp_dir, f"ui_dump_{int(time.time())}.xml")
            
            # 远程设备上的临时文件路径
            remote_path = "/sdcard/ui_dump_temp.xml"
            
            # 执行UI Automator命令 - 使用增强dump命令获取完整UI树
            # 确保有足够的权限访问sdcard
            self.device.shell("mkdir -p /sdcard/uiautomator")
            
            # 尝试使用不同的命令
            ui_dump_cmd = f'uiautomator dump --compressed {remote_path}'
            dump_output = self.device.shell(ui_dump_cmd)
            
            # 如果第一个命令失败，尝试使用标准命令
            if "UI hierchary dumped to" not in dump_output and "XML" not in dump_output:
                ui_dump_cmd = f'uiautomator dump {remote_path}'
                dump_output = self.device.shell(ui_dump_cmd)
                
                if "UI hierchary dumped to" not in dump_output and "XML" not in dump_output:
                    # 尝试第三种方式，有些设备需要指定完整路径
                    ui_dump_cmd = f'/system/bin/uiautomator dump {remote_path}'
                    dump_output = self.device.shell(ui_dump_cmd)
                    
                    if "UI hierchary dumped to" not in dump_output and "XML" not in dump_output:
                        result['message'] = f'UI Automator dump失败: {dump_output}'
                        return result
            
            # 从设备上拉取XML文件
            try:
                self.device.pull(remote_path, xml_temp_path)
                
                # 读取XML文件内容
                with open(xml_temp_path, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
                
                # 设置XML内容
                result['xml'] = xml_content
                
                # 解析XML提取元素信息
                try:
                    # 使用ElementTree解析XML - 递归获取所有元素
                    root = ET.fromstring(xml_content)
                    elements = []
                    
                    # 递归解析函数
                    def parse_node(node, depth=0, parent_index=None):
                        # 最大深度限制，防止递归过深
                        if depth > max_depth:
                            print(f"警告: 元素深度超过最大值 {max_depth}，停止解析子元素")
                            return None
                            
                        # 创建元素字典
                        element = {
                            'depth': depth,
                            'parent_index': parent_index,
                            'child_indices': []
                        }
                        
                        # 获取所有属性
                        for attr_name, attr_value in node.attrib.items():
                            if attr_name == 'bounds':
                                # 解析bounds属性 [x1,y1][x2,y2]
                                bounds_pattern = r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]'
                                bounds_match = re.search(bounds_pattern, attr_value)
                                if bounds_match:
                                    x1, y1, x2, y2 = map(int, bounds_match.groups())
                                    element[attr_name] = [x1, y1, x2, y2]
                            # 处理布尔值属性
                            elif attr_name in ['clickable', 'long-clickable', 'checkable', 
                                         'checked', 'enabled', 'focusable', 
                                         'focused', 'password', 'scrollable']:
                                element[attr_name] = attr_value.lower() == 'true'
                            else:
                                element[attr_name] = attr_value
                        
                        # 添加元素到列表，记录当前索引
                        current_index = len(elements)
                        elements.append(element)
                        
                        # 更新父元素的child_indices
                        if parent_index is not None and parent_index < len(elements):
                            elements[parent_index]['child_indices'].append(current_index)
                        
                        # 递归处理子节点
                        for child in node:
                            parse_node(child, depth + 1, current_index)
                            
                        return current_index
                    
                    # 从根节点开始解析
                    parse_node(root)
                    
                    # 获取元素总数和最大深度
                    max_element_depth = max([e.get('depth', 0) for e in elements]) if elements else 0
                    print(f"已解析 {len(elements)} 个UI元素，最大深度: {max_element_depth}")
                    
                    result['elements'] = elements
                    
                except Exception as parse_error:
                    print(f"XML递归解析失败: {parse_error}")
                    # 如果ElementTree解析失败，尝试使用传统的正则表达式方法作为备用
                    print("尝试使用备用解析方法...")
                    elements = []
                    
                    # 使用正则表达式解析XML中的节点（包括自闭和节点和带子节点的节点）
                    node_pattern = r'<node[^>]*?(?:/>|>.*?</node>)'
                    nodes = re.findall(node_pattern, xml_content, re.DOTALL)
                    
                    for node in nodes:
                        element = {}
                        
                        # 提取各种属性
                        attrs = [
                            'class', 'resource-id', 'package', 'content-desc', 'text',
                            'bounds', 'clickable', 'long-clickable', 'checkable',
                            'checked', 'enabled', 'focusable', 'focused', 'password',
                            'scrollable', 'index', 'NAF'
                        ]
                        
                        for attr in attrs:
                            pattern = f'{attr}="([^"]*)"'
                            match = re.search(pattern, node)
                            if match:
                                value = match.group(1)
                                
                                # 特殊处理bounds属性
                                if attr == 'bounds':
                                    # 格式通常为[x1,y1][x2,y2]
                                    bounds_pattern = r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]'
                                    bounds_match = re.search(bounds_pattern, value)
                                    if bounds_match:
                                        x1, y1, x2, y2 = map(int, bounds_match.groups())
                                        element[attr] = [x1, y1, x2, y2]
                                # 处理布尔值属性
                                elif attr in ['clickable', 'long-clickable', 'checkable', 
                                           'checked', 'enabled', 'focusable', 
                                           'focused', 'password', 'scrollable', 'NAF']:
                                    element[attr] = value.lower() == 'true'
                                else:
                                    element[attr] = value
                        
                        # 如果至少有基本属性，添加到元素列表
                        if 'class' in element:
                            element['depth'] = 0  # 备用方法无法确定深度
                            element['parent_index'] = None
                            element['child_indices'] = []
                            elements.append(element)
                    
                    # 尝试模拟父子关系
                    try:
                        # 通过位置关系推断父子关系
                        for i, element in enumerate(elements):
                            bounds_i = element.get('bounds', [])
                            if not bounds_i:
                                continue
                                
                            x1_i, y1_i, x2_i, y2_i = bounds_i
                            
                            # 查找可能的父元素
                            for j, potential_parent in enumerate(elements):
                                if i == j:  # 跳过自身
                                    continue
                                    
                                bounds_j = potential_parent.get('bounds', [])
                                if not bounds_j:
                                    continue
                                    
                                x1_j, y1_j, x2_j, y2_j = bounds_j
                                
                                # 如果元素完全包含在另一个元素内部，则它可能是子元素
                                if (x1_j <= x1_i and y1_j <= y1_i and 
                                    x2_j >= x2_i and y2_j >= y2_i and
                                    (x1_j != x1_i or y1_j != y1_i or x2_j != x2_i or y2_j != y2_i)):
                                    # 可能是父子关系
                                    element['parent_index'] = j
                                    if 'child_indices' not in potential_parent:
                                        potential_parent['child_indices'] = []
                                    potential_parent['child_indices'].append(i)
                                    break
                        
                        # 计算深度
                        for i, element in enumerate(elements):
                            depth = 0
                            parent_idx = element.get('parent_index')
                            while parent_idx is not None and parent_idx < len(elements):
                                depth += 1
                                parent_idx = elements[parent_idx].get('parent_index')
                            element['depth'] = depth
                            
                    except Exception as hierarchy_error:
                        print(f"模拟层次关系失败: {hierarchy_error}")
                    
                    # 获取元素总数和最大深度
                    max_element_depth = max([e.get('depth', 0) for e in elements]) if elements else 0
                    print(f"备用方法解析 {len(elements)} 个UI元素，最大深度: {max_element_depth}")
                    
                    result['elements'] = elements
                
                # 美化XML（可选）
                if pretty_print:
                    try:
                        dom = xml.dom.minidom.parseString(xml_content)
                        xml_content = dom.toprettyxml(indent="  ")
                        result['xml'] = xml_content
                        
                        # 如果需要保存XML，更新文件内容
                        if save_xml:
                            with open(xml_temp_path, 'w', encoding='utf-8') as f:
                                f.write(xml_content)
                    except Exception as xml_error:
                        print(f"XML美化失败: {xml_error}")
                
                # 保存XML文件路径（如果请求保存）
                if save_xml:
                    result['xml_file_path'] = xml_temp_path
                else:
                    # 如果不需要保存，删除临时文件
                    if os.path.exists(xml_temp_path):
                        os.remove(xml_temp_path)
                
                # 删除设备上的临时文件
                self.device.shell(f'rm {remote_path}')
                
                result['success'] = True
                result['message'] = f'成功获取UI结构，包含 {len(result["elements"])} 个元素'
                
            except Exception as pull_error:
                result['message'] = f'从设备拉取XML文件失败: {pull_error}'
                return result
                
            return result
            
        except Exception as e:
            result['message'] = f'获取UI结构时出错: {str(e)}'
            return result
    
    def click_element(self, element: Union[Dict[str, Any], int], 
                   click_type: str = 'click', wait_time: float = 0.5) -> Dict[str, Any]:
        """
        点击指定的UI元素
        
        Args:
            element: UI元素字典或元素索引
            click_type: 点击类型，可选值: "click"(单击), "long_click"(长按), "double_click"(双击)
            wait_time: 点击后等待时间(秒)
            
        Returns:
            操作结果，格式为：
            {
                'success': bool,
                'message': str,
                'click_position': [x, y]  # 点击的坐标
            }
        """
        result = {
            'success': False,
            'message': '',
            'click_position': None
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 获取要点击的元素
            target_element = None
            
            if isinstance(element, int):
                # 获取当前UI结构
                ui_info = self.get_current_app_ui(pretty_print=False)
                if not ui_info['success']:
                    result['message'] = f'获取UI结构失败: {ui_info["message"]}'
                    return result
                
                # 检查索引是否有效
                if element < 0 or element >= len(ui_info['elements']):
                    result['message'] = f'无效的元素索引: {element}'
                    return result
                
                target_element = ui_info['elements'][element]
            elif isinstance(element, dict) and 'bounds' in element:
                target_element = element
            else:
                result['message'] = '无效的元素参数，需要元素字典或有效的元素索引'
                return result
            
            # 确保元素有bounds属性
            if 'bounds' not in target_element or not target_element['bounds'] or len(target_element['bounds']) != 4:
                result['message'] = '元素缺少有效的bounds属性'
                return result
            
            # 获取元素中心坐标
            bounds = target_element['bounds']
            x1, y1, x2, y2 = bounds
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # 检查坐标是否合理
            if center_x <= 0 or center_y <= 0:
                result['message'] = f'无效的点击坐标: ({center_x}, {center_y})'
                return result
            
            # 根据点击类型执行操作
            if click_type == 'click':
                # 单击
                cmd = f'input tap {center_x} {center_y}'
                self.device.shell(cmd)
            elif click_type == 'long_click':
                # 长按（使用swipe命令在同一位置停留500ms实现长按）
                cmd = f'input swipe {center_x} {center_y} {center_x} {center_y} 500'
                self.device.shell(cmd)
            elif click_type == 'double_click':
                # 双击（连续执行两次点击）
                cmd = f'input tap {center_x} {center_y}'
                self.device.shell(cmd)
                time.sleep(0.1)  # 短暂等待
                self.device.shell(cmd)
            else:
                result['message'] = f'不支持的点击类型: {click_type}'
                return result
            
            # 等待指定时间
            if wait_time > 0:
                time.sleep(wait_time)
            
            # 设置结果
            result['success'] = True
            result['message'] = f'成功{click_type}元素'
            result['click_position'] = [center_x, center_y]
            
            return result
            
        except Exception as e:
            result['message'] = f'点击元素时出错: {str(e)}'
            return result
    
    def click_by_text(self, text: str, partial_match: bool = True, 
                     click_type: str = 'click', wait_time: float = 0.5) -> Dict[str, Any]:
        """
        通过文本内容查找并点击元素
        
        Args:
            text: 要查找的文本内容
            partial_match: 是否允许部分匹配，默认为True
            click_type: 点击类型，可选值: "click"(单击), "long_click"(长按), "double_click"(双击)
            wait_time: 点击后等待时间(秒)
            
        Returns:
            操作结果，格式同click_element
        """
        result = {
            'success': False,
            'message': '',
            'click_position': None,
            'matched_element': None
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 获取当前UI结构
            ui_info = self.get_current_app_ui(pretty_print=False)
            if not ui_info['success']:
                result['message'] = f'获取UI结构失败: {ui_info["message"]}'
                return result
            
            # 查找匹配文本的元素
            matched_elements = []
            
            for element in ui_info['elements']:
                element_text = element.get('text', '')
                element_desc = element.get('content-desc', '')
                
                if partial_match:
                    # 部分匹配
                    if text.lower() in element_text.lower() or text.lower() in element_desc.lower():
                        matched_elements.append(element)
                else:
                    # 完全匹配
                    if text == element_text or text == element_desc:
                        matched_elements.append(element)
            
            if not matched_elements:
                result['message'] = f'未找到包含文本 "{text}" 的元素'
                return result
            
            # 优先选择可点击的元素
            clickable_elements = [e for e in matched_elements if e.get('clickable', False)]
            
            if clickable_elements:
                target_element = clickable_elements[0]  # 使用第一个可点击元素
            else:
                target_element = matched_elements[0]  # 使用第一个匹配元素
            
            # 点击找到的元素
            click_result = self.click_element(target_element, click_type, wait_time)
            
            # 设置结果
            result['success'] = click_result['success']
            result['message'] = click_result['message']
            result['click_position'] = click_result['click_position']
            result['matched_element'] = target_element
            
            return result
            
        except Exception as e:
            result['message'] = f'通过文本点击元素时出错: {str(e)}'
            return result
    
    def click_by_resource_id(self, resource_id: str, partial_match: bool = False, 
                           click_type: str = 'click', wait_time: float = 0.5) -> Dict[str, Any]:
        """
        通过资源ID查找并点击元素
        
        Args:
            resource_id: 要查找的资源ID
            partial_match: 是否允许部分匹配，默认为False
            click_type: 点击类型，可选值: "click"(单击), "long_click"(长按), "double_click"(双击)
            wait_time: 点击后等待时间(秒)
            
        Returns:
            操作结果，格式同click_element
        """
        result = {
            'success': False,
            'message': '',
            'click_position': None,
            'matched_element': None
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 获取当前UI结构
            ui_info = self.get_current_app_ui(pretty_print=False)
            if not ui_info['success']:
                result['message'] = f'获取UI结构失败: {ui_info["message"]}'
                return result
            
            # 查找匹配资源ID的元素
            matched_elements = []
            
            for element in ui_info['elements']:
                element_id = element.get('resource-id', '')
                
                if partial_match:
                    # 部分匹配
                    if resource_id.lower() in element_id.lower():
                        matched_elements.append(element)
                else:
                    # 完全匹配
                    if resource_id == element_id:
                        matched_elements.append(element)
            
            if not matched_elements:
                result['message'] = f'未找到资源ID为 "{resource_id}" 的元素'
                return result
            
            # 优先选择可点击的元素
            clickable_elements = [e for e in matched_elements if e.get('clickable', False)]
            
            if clickable_elements:
                target_element = clickable_elements[0]  # 使用第一个可点击元素
            else:
                target_element = matched_elements[0]  # 使用第一个匹配元素
            
            # 点击找到的元素
            click_result = self.click_element(target_element, click_type, wait_time)
            
            # 设置结果
            result['success'] = click_result['success']
            result['message'] = click_result['message']
            result['click_position'] = click_result['click_position']
            result['matched_element'] = target_element
            
            return result
            
        except Exception as e:
            result['message'] = f'通过资源ID点击元素时出错: {str(e)}'
            return result
    
    def click_by_position(self, x: int, y: int, click_type: str = 'click', 
                        wait_time: float = 0.5) -> Dict[str, Any]:
        """
        通过坐标直接点击屏幕
        
        Args:
            x: 横坐标
            y: 纵坐标
            click_type: 点击类型，可选值: "click"(单击), "long_click"(长按), "double_click"(双击)
            wait_time: 点击后等待时间(秒)
            
        Returns:
            操作结果，格式为：
            {
                'success': bool,
                'message': str,
                'click_position': [x, y]  # 点击的坐标
            }
        """
        result = {
            'success': False,
            'message': '',
            'click_position': [x, y]
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 检查坐标是否合理
            if x <= 0 or y <= 0:
                result['message'] = f'无效的点击坐标: ({x}, {y})'
                return result
            
            # 根据点击类型执行操作
            if click_type == 'click':
                # 单击
                cmd = f'input tap {x} {y}'
                self.device.shell(cmd)
            elif click_type == 'long_click':
                # 长按（使用swipe命令在同一位置停留500ms实现长按）
                cmd = f'input swipe {x} {y} {x} {y} 500'
                self.device.shell(cmd)
            elif click_type == 'double_click':
                # 双击（连续执行两次点击）
                cmd = f'input tap {x} {y}'
                self.device.shell(cmd)
                time.sleep(0.1)  # 短暂等待
                self.device.shell(cmd)
            else:
                result['message'] = f'不支持的点击类型: {click_type}'
                return result
            
            # 等待指定时间
            if wait_time > 0:
                time.sleep(wait_time)
            
            # 设置结果
            result['success'] = True
            result['message'] = f'成功{click_type}坐标 ({x}, {y})'
            
            return result
            
        except Exception as e:
            result['message'] = f'点击坐标时出错: {str(e)}'
            return result
    
    def click_by_class(self, class_name: str, text: Optional[str] = None, index: int = 0,
                   partial_match: bool = True, click_type: str = 'click', 
                   wait_time: float = 0.5) -> Dict[str, Any]:
        """
        通过类名查找并点击元素
        
        Args:
            class_name: 要查找的类名，例如'android.view.ViewGroup'
            text: 可选的文本内容过滤，如果提供则同时匹配文本
            index: 匹配元素的索引，当有多个匹配元素时使用，默认为0(第一个)
            partial_match: 是否允许文本部分匹配，默认为True
            click_type: 点击类型，可选值: "click"(单击), "long_click"(长按), "double_click"(双击)
            wait_time: 点击后等待时间(秒)
            
        Returns:
            操作结果，格式同click_element
        """
        result = {
            'success': False,
            'message': '',
            'click_position': None,
            'matched_element': None,
            'match_count': 0
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 获取当前UI结构
            ui_info = self.get_current_app_ui(pretty_print=False)
            if not ui_info['success']:
                result['message'] = f'获取UI结构失败: {ui_info["message"]}'
                return result
            
            # 查找匹配类名的元素
            matched_elements = []
            
            for element in ui_info['elements']:
                element_class = element.get('class', '')
                
                # 类名匹配检查
                class_match = class_name == element_class
                
                # 如果还需检查文本
                text_match = True
                if text is not None:
                    element_text = element.get('text', '')
                    element_desc = element.get('content-desc', '')
                    
                    if partial_match:
                        # 部分匹配
                        text_match = (text.lower() in element_text.lower() or 
                                    text.lower() in element_desc.lower())
                    else:
                        # 完全匹配
                        text_match = (text == element_text or text == element_desc)
                
                # 如果类名和文本(如果提供)都匹配，则添加到匹配列表
                if class_match and text_match:
                    matched_elements.append(element)
            
            # 记录匹配数量
            result['match_count'] = len(matched_elements)
            
            if not matched_elements:
                result['message'] = f'未找到类名为 "{class_name}"'
                if text:
                    result['message'] += f' 且包含文本 "{text}"'
                result['message'] += ' 的元素'
                return result
            
            # 检查索引是否有效
            if index < 0 or index >= len(matched_elements):
                result['message'] = f'无效的索引: {index}，匹配元素数量为 {len(matched_elements)}'
                return result
            
            # 获取指定索引的元素
            target_element = matched_elements[index]
            
            # 点击找到的元素
            click_result = self.click_element(target_element, click_type, wait_time)
            
            # 设置结果
            result['success'] = click_result['success']
            result['message'] = click_result['message']
            result['click_position'] = click_result['click_position']
            result['matched_element'] = target_element
            
            return result
            
        except Exception as e:
            result['message'] = f'通过类名点击元素时出错: {str(e)}'
            return result
    
    def find_elements_by_class(self, class_name: str, text: Optional[str] = None, 
                             partial_match: bool = True) -> Dict[str, Any]:
        """
        查找特定类名的元素
        
        Args:
            class_name: 要查找的类名，例如'android.view.ViewGroup'
            text: 可选的文本内容过滤，如果提供则同时匹配文本
            partial_match: 是否允许文本部分匹配，默认为True
            
        Returns:
            查找结果，格式为：
            {
                'success': bool,
                'message': str,
                'elements': [元素列表],
                'count': int  # 匹配元素数量
            }
        """
        result = {
            'success': False,
            'message': '',
            'elements': [],
            'count': 0
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 获取当前UI结构
            ui_info = self.get_current_app_ui(pretty_print=False)
            if not ui_info['success']:
                result['message'] = f'获取UI结构失败: {ui_info["message"]}'
                return result
            
            # 查找匹配类名的元素
            matched_elements = []
            
            for element in ui_info['elements']:
                element_class = element.get('class', '')
                
                # 类名匹配检查
                class_match = class_name == element_class
                
                # 如果还需检查文本
                text_match = True
                if text is not None:
                    element_text = element.get('text', '')
                    element_desc = element.get('content-desc', '')
                    
                    if partial_match:
                        # 部分匹配
                        text_match = (text.lower() in element_text.lower() or 
                                    text.lower() in element_desc.lower())
                    else:
                        # 完全匹配
                        text_match = (text == element_text or text == element_desc)
                
                # 如果类名和文本(如果提供)都匹配，则添加到匹配列表
                if class_match and text_match:
                    matched_elements.append(element)
            
            # 设置结果
            result['success'] = True
            result['count'] = len(matched_elements)
            result['elements'] = matched_elements
            
            if matched_elements:
                result['message'] = f'找到 {len(matched_elements)} 个匹配元素'
            else:
                result['message'] = f'未找到类名为 "{class_name}"'
                if text:
                    result['message'] += f' 且包含文本 "{text}"'
                result['message'] += ' 的元素'
            
            return result
            
        except Exception as e:
            result['message'] = f'查找元素时出错: {str(e)}'
            return result
    
    def find_scrollable_elements(self) -> Dict[str, Any]:
        """
        查找当前UI中所有可滚动元素
        
        Returns:
            查找结果，格式为：
            {
                'success': bool,
                'message': str,
                'elements': [可滚动元素列表],
                'count': int  # 可滚动元素数量
            }
        """
        result = {
            'success': False,
            'message': '',
            'elements': [],
            'count': 0
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 获取当前UI结构
            ui_info = self.get_current_app_ui(pretty_print=False)
            if not ui_info['success']:
                result['message'] = f'获取UI结构失败: {ui_info["message"]}'
                return result
            
            # 筛选可滚动元素
            scrollable_elements = []
            
            for element in ui_info['elements']:
                if element.get('scrollable', False):
                    scrollable_elements.append(element)
            
            # 设置结果
            result['success'] = True
            result['count'] = len(scrollable_elements)
            result['elements'] = scrollable_elements
            
            if scrollable_elements:
                result['message'] = f'找到 {len(scrollable_elements)} 个可滚动元素'
            else:
                result['message'] = '未找到可滚动元素'
            
            return result
            
        except Exception as e:
            result['message'] = f'查找可滚动元素时出错: {str(e)}'
            return result
    
    def scroll_element(self, element: Union[Dict[str, Any], int], direction: str = 'down', 
                     distance: float = 0.5, duration: int = 300) -> Dict[str, Any]:
        """
        滚动指定元素
        
        Args:
            element: 元素字典或元素索引
            direction: 滚动方向，可选值: "up", "down", "left", "right"
            distance: 滚动距离，相对于元素尺寸的比例，范围0.1-1.0，默认为0.5
            duration: 滚动持续时间(毫秒)，默认为300ms
            
        Returns:
            操作结果，格式为：
            {
                'success': bool,
                'message': str,
                'scroll_info': {
                    'start': [x, y],
                    'end': [x, y],
                    'direction': str,
                    'distance': float,
                    'duration': int
                }
            }
        """
        result = {
            'success': False,
            'message': '',
            'scroll_info': None
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 获取要滚动的元素
            target_element = None
            
            if isinstance(element, int):
                # 获取当前UI结构
                ui_info = self.get_current_app_ui(pretty_print=False)
                if not ui_info['success']:
                    result['message'] = f'获取UI结构失败: {ui_info["message"]}'
                    return result
                
                # 检查索引是否有效
                if element < 0 or element >= len(ui_info['elements']):
                    result['message'] = f'无效的元素索引: {element}'
                    return result
                
                target_element = ui_info['elements'][element]
            elif isinstance(element, dict) and 'bounds' in element:
                target_element = element
            else:
                result['message'] = '无效的元素参数，需要元素字典或有效的元素索引'
                return result
            
            # 确保元素有bounds属性
            if 'bounds' not in target_element or not target_element['bounds'] or len(target_element['bounds']) != 4:
                result['message'] = '元素缺少有效的bounds属性'
                return result
            
            # 确保距离参数有效
            if distance < 0.1 or distance > 1.0:
                distance = 0.5  # 默认使用0.5
            
            # 确保持续时间有效
            if duration < 50:
                duration = 300  # 默认使用300ms
            
            # 获取元素边界
            bounds = target_element['bounds']
            x1, y1, x2, y2 = bounds
            width = x2 - x1
            height = y2 - y1
            
            # 计算滚动起点和终点
            start_x, start_y = None, None
            end_x, end_y = None, None
            
            # 根据方向计算坐标
            if direction == 'down':
                # 从元素中心下方向上滚动
                start_x = x1 + width // 2
                start_y = y1 + int(height * 0.7)
                end_x = start_x
                end_y = y1 + int(height * (0.7 - distance))
            elif direction == 'up':
                # 从元素中心上方向下滚动
                start_x = x1 + width // 2
                start_y = y1 + int(height * 0.3)
                end_x = start_x
                end_y = y1 + int(height * (0.3 + distance))
            elif direction == 'right':
                # 从元素中心右侧向左滚动
                start_x = x1 + int(width * 0.7)
                start_y = y1 + height // 2
                end_x = x1 + int(width * (0.7 - distance))
                end_y = start_y
            elif direction == 'left':
                # 从元素中心左侧向右滚动
                start_x = x1 + int(width * 0.3)
                start_y = y1 + height // 2
                end_x = x1 + int(width * (0.3 + distance))
                end_y = start_y
            else:
                result['message'] = f'不支持的滚动方向: {direction}'
                return result
            
            # 执行滚动命令
            cmd = f'input swipe {start_x} {start_y} {end_x} {end_y} {duration}'
            self.device.shell(cmd)
            
            # 设置滚动信息
            scroll_info = {
                'start': [start_x, start_y],
                'end': [end_x, end_y],
                'direction': direction,
                'distance': distance,
                'duration': duration
            }
            
            # 设置结果
            result['success'] = True
            result['message'] = f'成功向{direction}滚动元素'
            result['scroll_info'] = scroll_info
            
            return result
            
        except Exception as e:
            result['message'] = f'滚动元素时出错: {str(e)}'
            return result
    
    def scroll_screen(self, direction: str = 'down', distance: float = 0.5, 
                    duration: int = 300) -> Dict[str, Any]:
        """
        滚动屏幕(不针对特定元素)
        
        Args:
            direction: 滚动方向，可选值: "up", "down", "left", "right"
            distance: 滚动距离，相对于屏幕尺寸的比例，范围0.1-1.0，默认为0.5
            duration: 滚动持续时间(毫秒)，默认为300ms
            
        Returns:
            操作结果，格式同scroll_element
        """
        result = {
            'success': False,
            'message': '',
            'scroll_info': None
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 获取屏幕尺寸
            screen_size_cmd = 'wm size'
            size_output = self.device.shell(screen_size_cmd)
            
            # 解析屏幕尺寸
            width, height = 1080, 1920  # 默认值
            size_match = re.search(r'Physical size: (\d+)x(\d+)', size_output)
            if size_match:
                width = int(size_match.group(1))
                height = int(size_match.group(2))
            else:
                # 尝试其他格式
                size_match = re.search(r'(\d+)x(\d+)', size_output)
                if size_match:
                    width = int(size_match.group(1))
                    height = int(size_match.group(2))
            
            # 确保距离参数有效
            if distance < 0.1 or distance > 1.0:
                distance = 0.5  # 默认使用0.5
            
            # 确保持续时间有效
            if duration < 50:
                duration = 300  # 默认使用300ms
            
            # 计算滚动起点和终点
            start_x, start_y = None, None
            end_x, end_y = None, None
            
            # 根据方向计算坐标
            if direction == 'down':
                # 从屏幕中心下方向上滑动
                start_x = width // 2
                start_y = int(height * 0.7)
                end_x = start_x
                end_y = int(height * (0.7 - distance))
            elif direction == 'up':
                # 从屏幕中心上方向下滑动
                start_x = width // 2
                start_y = int(height * 0.3)
                end_x = start_x
                end_y = int(height * (0.3 + distance))
            elif direction == 'right':
                # 从屏幕中心右侧向左滑动
                start_x = int(width * 0.7)
                start_y = height // 2
                end_x = int(width * (0.7 - distance))
                end_y = start_y
            elif direction == 'left':
                # 从屏幕中心左侧向右滑动
                start_x = int(width * 0.3)
                start_y = height // 2
                end_x = int(width * (0.3 + distance))
                end_y = start_y
            else:
                result['message'] = f'不支持的滚动方向: {direction}'
                return result
            
            # 执行滚动命令
            cmd = f'input swipe {start_x} {start_y} {end_x} {end_y} {duration}'
            self.device.shell(cmd)
            
            # 设置滚动信息
            scroll_info = {
                'start': [start_x, start_y],
                'end': [end_x, end_y],
                'direction': direction,
                'distance': distance,
                'duration': duration
            }
            
            # 设置结果
            result['success'] = True
            result['message'] = f'成功向{direction}滚动屏幕'
            result['scroll_info'] = scroll_info
            
            return result
            
        except Exception as e:
            result['message'] = f'滚动屏幕时出错: {str(e)}'
            return result
    
    def auto_scroll_all(self, max_attempts: int = 5, directions: List[str] = None, 
                      wait_time: float = 1.0) -> Dict[str, Any]:
        """
        尝试滚动当前UI中所有可滚动元素，用于UI探索
        
        Args:
            max_attempts: 每个可滚动元素的最大尝试次数，默认5次
            directions: 要尝试的滚动方向列表，默认为['down', 'up']
            wait_time: 每次滚动后的等待时间(秒)，默认为1秒
            
        Returns:
            操作结果，格式为：
            {
                'success': bool,
                'message': str,
                'scrolled_elements': int,  # 成功滚动的元素数量
                'total_scrolls': int,      # 总滚动次数
                'scroll_results': [        # 各元素的滚动结果
                    {
                        'element_index': int,  # 元素索引
                        'element_info': {},    # 元素信息
                        'directions': [        # 各方向的滚动结果
                            {
                                'direction': str,
                                'success': bool,
                                'attempts': int
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }
        """
        result = {
            'success': False,
            'message': '',
            'scrolled_elements': 0,
            'total_scrolls': 0,
            'scroll_results': []
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 设置默认方向
            if not directions:
                directions = ['down', 'up']
            
            # 获取当前UI中所有可滚动元素
            scrollable_result = self.find_scrollable_elements()
            if not scrollable_result['success']:
                result['message'] = f'查找可滚动元素失败: {scrollable_result["message"]}'
                return result
            
            if scrollable_result['count'] == 0:
                result['message'] = '未找到可滚动元素'
                result['success'] = True
                return result
            
            # 记录已成功滚动的元素数量和总滚动次数
            scrolled_elements = 0
            total_scrolls = 0
            scroll_results = []
            
            # 逐个尝试滚动可滚动元素
            for element_index, element in enumerate(scrollable_result['elements']):
                element_result = {
                    'element_index': element_index,
                    'element_info': {
                        'class': element.get('class', 'Unknown'),
                        'text': element.get('text', ''),
                        'content-desc': element.get('content-desc', ''),
                        'resource-id': element.get('resource-id', ''),
                        'bounds': element.get('bounds', [])
                    },
                    'directions': []
                }
                
                element_scrolled = False
                
                # 尝试各个方向的滚动
                for direction in directions:
                    direction_result = {
                        'direction': direction,
                        'success': False,
                        'attempts': 0
                    }
                    
                    # 对每个方向尝试多次滚动，直到无法继续滚动或达到最大尝试次数
                    for attempt in range(max_attempts):
                        # 执行滚动
                        scroll_result = self.scroll_element(element, direction=direction)
                        direction_result['attempts'] += 1
                        total_scrolls += 1
                        
                        if scroll_result['success']:
                            direction_result['success'] = True
                            element_scrolled = True
                            
                            # 等待界面刷新
                            time.sleep(wait_time)
                        else:
                            # 如果滚动失败，不再尝试该方向
                            break
                    
                    # 添加该方向的结果
                    element_result['directions'].append(direction_result)
                
                # 添加该元素的结果
                scroll_results.append(element_result)
                
                # 如果成功滚动过该元素，增加计数
                if element_scrolled:
                    scrolled_elements += 1
            
            # 设置结果
            result['success'] = True
            result['message'] = f'尝试滚动 {scrollable_result["count"]} 个可滚动元素，成功滚动 {scrolled_elements} 个，总滚动次数 {total_scrolls}'
            result['scrolled_elements'] = scrolled_elements
            result['total_scrolls'] = total_scrolls
            result['scroll_results'] = scroll_results
            
            return result
            
        except Exception as e:
            result['message'] = f'自动滚动UI时出错: {str(e)}'
            return result
    

    
    def capture_screenshot(self, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        捕获设备屏幕截图
        
        Args:
            save_path: 保存截图的路径，如果为None则使用临时目录和时间戳命名
            
        Returns:
            截图结果，格式为：
            {
                'success': bool,
                'message': str,
                'screenshot_path': str  # 截图保存路径
            }
        """
        result = {
            'success': False,
            'message': '',
            'screenshot_path': ''
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 创建临时文件路径用于保存截图
            if save_path:
                screenshot_path = save_path
                # 确保目录存在
                os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            else:
                # 使用临时目录和时间戳
                temp_dir = os.path.join(tempfile.gettempdir(), 'ppadb_screenshots')
                os.makedirs(temp_dir, exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(temp_dir, f"screenshot_{timestamp}.png")
            
            # 远程设备上的临时文件路径
            remote_path = "/sdcard/screenshot_temp.png"
            
            # 执行截图命令
            self.device.shell("screencap -p " + remote_path)
            
            # 从设备上拉取截图文件
            try:
                self.device.pull(remote_path, screenshot_path)
                
                # 删除设备上的临时文件
                self.device.shell(f"rm {remote_path}")
                
                result['success'] = True
                result['message'] = '成功捕获屏幕截图'
                result['screenshot_path'] = screenshot_path
                
            except Exception as pull_error:
                result['message'] = f'从设备拉取截图失败: {pull_error}'
                return result
                
            return result
            
        except Exception as e:
            result['message'] = f'截图时出错: {str(e)}'
            return result
    
    def capture_and_mark_chat(self, save_path: Optional[str] = None, 
                            mark_messages: bool = True, 
                            mark_chat_area: bool = True) -> Dict[str, Any]:
        """
        捕获屏幕截图并标记聊天区域和消息位置
        
        Args:
            save_path: 保存标记后截图的路径
            mark_messages: 是否标记消息位置
            mark_chat_area: 是否标记聊天区域
            
        Returns:
            标记结果，格式为：
            {
                'success': bool,
                'message': str,
                'original_screenshot': str,  # 原始截图路径
                'marked_screenshot': str,    # 标记后截图路径
                'chat_result': dict          # 聊天分析结果
            }
        """
        result = {
            'success': False,
            'message': '',
            'original_screenshot': '',
            'marked_screenshot': '',
            'chat_result': {}
        }
        
        try:
            # 尝试导入PIL库用于图像处理
            try:
                from PIL import Image, ImageDraw, ImageFont
            except ImportError:
                result['message'] = '未安装PIL库，无法进行图像标记'
                return result
            
            # 捕获屏幕截图
            screenshot_result = self.capture_screenshot()
            if not screenshot_result['success']:
                result['message'] = f'截图失败: {screenshot_result["message"]}'
                return result
            
            original_screenshot = screenshot_result['screenshot_path']
            result['original_screenshot'] = original_screenshot
            
            # 分析聊天消息
            chat_result = self.get_chat_messages()
            result['chat_result'] = chat_result
            
            if not chat_result['success']:
                result['message'] = f'分析聊天失败: {chat_result["message"]}'
                return result
            
            # 创建标记后的截图路径
            if save_path:
                marked_screenshot = save_path
                os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            else:
                temp_dir = os.path.join(tempfile.gettempdir(), 'ppadb_screenshots')
                os.makedirs(temp_dir, exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                marked_screenshot = os.path.join(temp_dir, f"chat_marked_{timestamp}.png")
            
            # 打开原始截图
            img = Image.open(original_screenshot)
            draw = ImageDraw.Draw(img)
            
            # 尝试加载字体，如果失败则使用默认字体
            try:
                # 使用系统默认字体
                if os.name == 'nt':  # Windows
                    font_path = "C:\\Windows\\Fonts\\simhei.ttf"
                else:  # Linux/Mac
                    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                
                font = ImageFont.truetype(font_path, 14)
                small_font = ImageFont.truetype(font_path, 12)
            except:
                # 使用默认字体
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # 标记聊天区域
            if mark_chat_area and chat_result['chat_area']['bounds']:
                bounds = chat_result['chat_area']['bounds']
                # 绘制矩形
                draw.rectangle([(bounds[0], bounds[1]), (bounds[2], bounds[3])], 
                              outline=(255, 0, 0), width=2)  # 红色
                
                # 标注说明
                draw.text((bounds[0], bounds[1] - 15), "聊天区域", 
                         fill=(255, 0, 0), font=font)
            
            # 标记消息位置
            if mark_messages and chat_result['messages']:
                # 为不同发送者使用不同颜色
                colors = {
                    'self': (0, 255, 0),     # 绿色
                    'other': (0, 0, 255),    # 蓝色
                    'system': (255, 255, 0), # 黄色
                    'unknown': (128, 128, 128)  # 灰色
                }
                
                for i, message in enumerate(chat_result['messages']):
                    if 'bounds' in message and message['bounds']:
                        bounds = message['bounds']
                        sender = message['sender']
                        color = colors.get(sender, colors['unknown'])
                        
                        # 绘制消息边框
                        draw.rectangle([(bounds[0], bounds[1]), (bounds[2], bounds[3])], 
                                      outline=color, width=1)
                        
                        # 标注消息序号和类型
                        msg_type = message['type']
                        label = f"#{i+1} [{msg_type}]"
                        
                        # 标注文本（精简版本避免过长）
                        text = message['text']
                        if len(text) > 15:
                            text = text[:12] + "..."
                        
                        # 在消息框上方显示标签
                        draw.text((bounds[0], bounds[1] - 12), label, 
                                 fill=color, font=small_font)
            
            # 保存标记后的图像
            img.save(marked_screenshot)
            result['marked_screenshot'] = marked_screenshot
            
            result['success'] = True
            result['message'] = f'成功标记聊天截图，标记了 {len(chat_result["messages"])} 条消息'
            
            return result
            
        except Exception as e:
            result['message'] = f'标记聊天截图时出错: {str(e)}'
            return result
    
    def capture_and_mark_all_elements(self, save_path: Optional[str] = None,
                                 highlight_special: bool = True,
                                 max_elements: int = 200) -> Dict[str, Any]:
        """
        捕获屏幕截图并标记所有UI组件位置
        
        Args:
            save_path: 保存标记后截图的路径
            highlight_special: 是否高亮显示特殊元素(可点击、可滚动等)
            max_elements: 最多标记的元素数量，避免过多元素导致图片混乱
            
        Returns:
            标记结果，格式为：
            {
                'success': bool,
                'message': str,
                'original_screenshot': str,  # 原始截图路径
                'marked_screenshot': str,    # 标记后截图路径
                'ui_info': dict              # UI分析结果
            }
        """
        result = {
            'success': False,
            'message': '',
            'original_screenshot': '',
            'marked_screenshot': '',
            'ui_info': {}
        }
        
        try:
            # 尝试导入PIL库用于图像处理
            try:
                from PIL import Image, ImageDraw, ImageFont
            except ImportError:
                result['message'] = '未安装PIL库，无法进行图像标记'
                return result
            
            # 捕获屏幕截图
            screenshot_result = self.capture_screenshot()
            if not screenshot_result['success']:
                result['message'] = f'截图失败: {screenshot_result["message"]}'
                return result
            
            original_screenshot = screenshot_result['screenshot_path']
            result['original_screenshot'] = original_screenshot
            
            # 获取UI结构
            ui_info = self.get_current_app_ui(pretty_print=False)
            result['ui_info'] = ui_info
            
            if not ui_info['success']:
                result['message'] = f'获取UI结构失败: {ui_info["message"]}'
                return result
            
            # 创建标记后的截图路径
            if save_path:
                marked_screenshot = save_path
                os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            else:
                temp_dir = os.path.join(tempfile.gettempdir(), 'ppadb_screenshots')
                os.makedirs(temp_dir, exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                marked_screenshot = os.path.join(temp_dir, f"ui_elements_{timestamp}.png")
            
            # 打开原始截图
            img = Image.open(original_screenshot)
            draw = ImageDraw.Draw(img)
            
            # 尝试加载字体，如果失败则使用默认字体
            try:
                # 使用系统默认字体
                if os.name == 'nt':  # Windows
                    font_path = "C:\\Windows\\Fonts\\simhei.ttf"
                else:  # Linux/Mac
                    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                
                font = ImageFont.truetype(font_path, 10)
                small_font = ImageFont.truetype(font_path, 8)
            except:
                # 使用默认字体
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # 标记所有UI元素
            elements_count = len(ui_info['elements'])
            marked_count = 0
            
            # 根据深度对元素进行排序，先绘制深度较大的元素
            sorted_elements = sorted(
                ui_info['elements'], 
                key=lambda x: x.get('depth', 0) if 'depth' in x else 0, 
                reverse=True
            )
            
            # 限制元素数量，避免过多标记导致图片混乱
            if max_elements > 0 and len(sorted_elements) > max_elements:
                sorted_elements = sorted_elements[:max_elements]
            
            # 记录已绘制的边界，避免重复标记同一区域
            drawn_bounds = set()
            
            for element in sorted_elements:
                if 'bounds' not in element or not element['bounds'] or len(element['bounds']) != 4:
                    continue
                
                bounds = element['bounds']
                bounds_tuple = tuple(bounds)  # 转换为元组以便用于set操作
                
                # 检查边界是否已经绘制过
                if bounds_tuple in drawn_bounds:
                    continue
                
                drawn_bounds.add(bounds_tuple)
                
                # 确定元素颜色
                color = (128, 128, 128)  # 默认灰色
                
                # 高亮显示特殊元素
                if highlight_special:
                    if element.get('clickable', False):
                        color = (0, 255, 0)  # 可点击元素为绿色
                    elif element.get('scrollable', False):
                        color = (255, 0, 0)  # 可滚动元素为红色
                    elif element.get('focusable', False):
                        color = (255, 165, 0)  # 可获取焦点元素为橙色
                    elif element.get('long-clickable', False):
                        color = (0, 0, 255)  # 可长按元素为蓝色
                    elif element.get('enabled', False) and element.get('class', '').endswith('EditText'):
                        color = (128, 0, 128)  # 输入框为紫色
                
                # 根据元素类型调整线宽
                line_width = 1
                if element.get('clickable', False) or element.get('scrollable', False):
                    line_width = 2
                
                # 绘制元素边框
                draw.rectangle([(bounds[0], bounds[1]), (bounds[2], bounds[3])], 
                               outline=color, width=line_width)
                
                # 准备标签文本
                element_class = element.get('class', '').split('.')[-1]  # 只取类名的最后部分
                element_text = element.get('text', '')
                element_desc = element.get('content-desc', '')
                element_id = element.get('resource-id', '').split('/')[-1] if 'resource-id' in element else ''
                
                # 组合标签文本，优先使用更有意义的信息
                label_parts = []
                
                # 添加元素序号
                element_index = ui_info['elements'].index(element)
                label_parts.append(f"#{element_index}")
                
                # 添加类型
                if element_class:
                    label_parts.append(element_class)
                
                # 准备属性标记
                attrs = []
                if element.get('clickable', False):
                    attrs.append('C')  # Clickable
                if element.get('scrollable', False):
                    attrs.append('S')  # Scrollable
                if element.get('long-clickable', False):
                    attrs.append('L')  # Long-clickable
                    
                if attrs:
                    label_parts.append(''.join(attrs))
                
                # 构建标签文本
                label = ' '.join(label_parts)
                
                # 绘制标签
                text_x = bounds[0]
                text_y = bounds[1] - 10 if bounds[1] > 10 else bounds[1]
                draw.text((text_x, text_y), label, fill=color, font=small_font)
                
                # 如果元素有文本内容，显示在右侧或下方
                display_text = None
                if element_text:
                    display_text = element_text
                elif element_desc:
                    display_text = element_desc
                elif element_id:
                    display_text = element_id
                
                if display_text:
                    # 限制文本长度，避免过长
                    if len(display_text) > 20:
                        display_text = display_text[:17] + "..."
                    
                    # 选择显示位置：优先右侧，如果空间不足则在下方
                    screen_width = img.width
                    text_width = len(display_text) * 6  # 估算宽度
                    
                    if bounds[0] + text_width < screen_width - 10:
                        # 右侧有足够空间
                        text_x = bounds[2] + 2
                        text_y = bounds[1]
                    else:
                        # 在元素下方显示
                        text_x = bounds[0]
                        text_y = bounds[3] + 2
                    
                    draw.text((text_x, text_y), display_text, fill=color, font=small_font)
                
                marked_count += 1
            
            # 添加图例
            legend_y = 10
            if highlight_special:
                # 绘制图例
                legend_items = [
                    ((0, 255, 0), "可点击元素"),
                    ((255, 0, 0), "可滚动元素"),
                    ((0, 0, 255), "可长按元素"),
                    ((255, 165, 0), "可获取焦点"),
                    ((128, 0, 128), "输入框"),
                    ((128, 128, 128), "普通元素")
                ]
                
                for idx, (color, text) in enumerate(legend_items):
                    pos_y = legend_y + idx * 15
                    draw.rectangle([(10, pos_y), (30, pos_y + 10)], outline=color, fill=color)
                    draw.text((35, pos_y), text, fill=(0, 0, 0), font=font)
            
            # 添加当前应用信息
            app_info = f"应用: {ui_info['package_name']}"
            if 'activity_name' in ui_info and ui_info['activity_name']:
                app_info += f" | 活动: {ui_info['activity_name']}"
            
            draw.text((10, img.height - 20), app_info, fill=(0, 0, 0), font=font)
            draw.text((10, img.height - 35), f"元素总数: {elements_count}, 已标记: {marked_count}", fill=(0, 0, 0), font=font)
            
            # 保存标记后的图像
            img.save(marked_screenshot)
            result['marked_screenshot'] = marked_screenshot
            
            result['success'] = True
            result['message'] = f'成功标记UI元素，共标记了 {marked_count} 个元素'
            
            return result
            
        except Exception as e:
            result['message'] = f'标记UI元素时出错: {str(e)}'
            return result
    
    def identify_list_structures(self, ui_result: Optional[Dict[str, Any]] = None, 
                              similarity_threshold: float = 0.8,
                              min_items: int = 2) -> Dict[str, Any]:
        """
        识别UI中的列表结构
        
        通过分析UI元素的层次结构，识别可能存在的列表。
        算法思路：从叶子节点向上合并，如果子节点大部分类型一致，则认为父节点是列表容器。
        
        Args:
            ui_result: UI分析结果，如果为None则自动获取当前UI
            similarity_threshold: 子元素相似度阈值，用于判断是否为列表项，默认0.8
            min_items: 列表最少包含的项数，默认为2
            
        Returns:
            列表结构信息，格式为：
            {
                'success': bool,
                'message': str,
                'lists': [
                    {
                        'root_index': int,         # 列表根节点索引
                        'root_element': dict,      # 列表根节点元素
                        'item_indices': [int],     # 列表项元素索引
                        'item_count': int,         # 列表项数量
                        'item_class': str,         # 列表项主要类型
                        'is_nested': bool,         # 是否为嵌套列表
                        'parent_list_index': int,  # 父列表索引(如果是嵌套列表)
                        'depth': int,              # 嵌套深度
                        'has_siblings': bool,      # 根节点是否有同级节点
                        'child_list_indices': [int]  # 子列表的索引列表
                    },
                    ...更多列表
                ],
                'list_count': int                  # 识别出的列表总数
            }
        """
        result = {
            'success': False,
            'message': '',
            'lists': [],
            'list_count': 0
        }
        
        if not self.device:
            result['message'] = '未连接设备'
            return result
            
        try:
            # 如果没有提供UI结果，则获取当前UI
            if ui_result is None:
                ui_info = self.get_current_app_ui(pretty_print=False)
                if not ui_info['success']:
                    result['message'] = f'获取UI结构失败: {ui_info["message"]}'
                    return result
                ui_result = ui_info
            
            # 获取UI元素列表
            elements = ui_result.get('elements', [])
            if not elements:
                result['message'] = '无UI元素数据'
                return result
            
            # 1. 构建辅助数据结构，找出所有叶子节点和所有父节点
            leaf_nodes = []  # 叶子节点（没有子节点的元素）
            parent_nodes = {}  # 父节点字典，键为父节点索引，值为子节点索引列表
            
            for i, element in enumerate(elements):
                child_indices = element.get('child_indices', [])
                if not child_indices:
                    leaf_nodes.append(i)
                else:
                    parent_nodes[i] = child_indices
            
            # 2. 预处理 - 构建元素之间的层次关系图
            # 存储每个元素的所有祖先元素
            element_ancestors = {}
            for i in range(len(elements)):
                ancestors = set()
                curr = i
                while True:
                    parent_idx = elements[curr].get('parent_index')
                    if parent_idx is None or parent_idx == curr:
                        break
                    ancestors.add(parent_idx)
                    curr = parent_idx
                element_ancestors[i] = ancestors
            
            # 3. 识别可能的列表结构
            potential_lists = []
            processed_parents = set()  # 已处理过的父节点
            
            # 检查子元素相似度的函数
            def check_children_similarity(parent_idx):
                children = parent_nodes.get(parent_idx, [])
                if len(children) < min_items:  # 至少需要指定数量子元素才能构成列表
                    return None
                
                # 统计子元素类型
                child_classes = {}
                for child_idx in children:
                    child = elements[child_idx]
                    child_class = child.get('class', 'Unknown')
                    child_classes[child_class] = child_classes.get(child_class, 0) + 1
                
                # 计算主要类型的子元素占比
                if not child_classes:
                    return None
                    
                main_class, main_count = max(child_classes.items(), key=lambda x: x[1])
                similarity_ratio = main_count / len(children)
                
                # 如果相似度达到阈值，则认为是列表项
                if similarity_ratio >= similarity_threshold:
                    similar_items = [idx for idx in children 
                                    if elements[idx].get('class', '') == main_class]
                    return {
                        'root_index': parent_idx,
                        'root_element': elements[parent_idx],
                        'item_indices': similar_items,
                        'item_count': len(similar_items),
                        'item_class': main_class,
                        'is_nested': False,
                        'parent_list_index': None,
                        'depth': elements[parent_idx].get('depth', 0),
                        'has_siblings': False,  # 默认值，后续会更新
                        'child_list_indices': [],  # 记录子列表索引
                        'ancestor_indices': element_ancestors.get(parent_idx, set())  # 记录祖先元素
                    }
                return None
            
            # 4. 从父节点中寻找列表结构
            for parent_idx in parent_nodes:
                # 如果已处理过，跳过
                if parent_idx in processed_parents:
                    continue
                    
                list_info = check_children_similarity(parent_idx)
                if list_info:
                    # 标记该父节点已处理
                    processed_parents.add(parent_idx)
                    
                    # 检查父节点是否有同级节点
                    parent_element = elements[parent_idx]
                    parent_of_parent_idx = parent_element.get('parent_index')
                    if parent_of_parent_idx is not None:
                        siblings = [idx for idx in parent_nodes.get(parent_of_parent_idx, []) 
                                  if idx != parent_idx]
                        list_info['has_siblings'] = len(siblings) > 0
                        
                        # 检查同级节点是否也是类似结构（可能是多个列表）
                        if list_info['has_siblings']:
                            sibling_lists = []
                            for sibling_idx in siblings:
                                sibling_list = check_children_similarity(sibling_idx)
                                if sibling_list and sibling_list['item_class'] == list_info['item_class']:
                                    sibling_lists.append(sibling_list)
                                    processed_parents.add(sibling_idx)
                            
                            # 如果同级节点也是列表，考虑是否为嵌套列表
                            if sibling_lists:
                                # 检查是否父节点本身也可以构成列表
                                parent_of_parent = elements[parent_of_parent_idx]
                                parent_class = parent_element.get('class', '')
                                siblings_same_class = all(elements[idx].get('class', '') == parent_class 
                                                        for idx in siblings)
                                
                                if siblings_same_class and len(siblings) > 0:
                                    # 可能是嵌套列表的情况
                                    nested_list = {
                                        'root_index': parent_of_parent_idx,
                                        'root_element': parent_of_parent,
                                        'item_indices': [parent_idx] + siblings,
                                        'item_count': len(siblings) + 1,
                                        'item_class': parent_class,
                                        'is_nested': True,
                                        'parent_list_index': None,
                                        'depth': parent_of_parent.get('depth', 0),
                                        'has_siblings': False,  # 将在之后更新
                                        'child_list_indices': [len(potential_lists)],  # 添加当前列表为子列表
                                        'ancestor_indices': element_ancestors.get(parent_of_parent_idx, set())  # 记录祖先元素
                                    }
                                    
                                    # 将当前列表及同级列表标记为嵌套列表的子项
                                    list_info['is_nested'] = True
                                    list_info['parent_list_index'] = len(potential_lists)
                                    
                                    for sibling_list in sibling_lists:
                                        sibling_list['is_nested'] = True
                                        sibling_list['parent_list_index'] = len(potential_lists)
                                        nested_list['child_list_indices'].append(len(potential_lists) + 1 + sibling_lists.index(sibling_list))
                                    
                                    # 先添加嵌套的父列表
                                    potential_lists.append(nested_list)
                                    processed_parents.add(parent_of_parent_idx)
                    
                    # 添加当前列表
                    potential_lists.append(list_info)
            
            # 5. 更新嵌套关系和层次深度
            for i, list_info in enumerate(potential_lists):
                parent_list_index = list_info.get('parent_list_index')
                if parent_list_index is not None and parent_list_index < len(potential_lists):
                    # 如果有父列表，更新嵌套深度
                    parent_depth = potential_lists[parent_list_index]['depth']
                    list_info['depth'] = parent_depth + 1
                    
                    # 将自己添加到父列表的子列表索引中
                    if i not in potential_lists[parent_list_index]['child_list_indices']:
                        potential_lists[parent_list_index]['child_list_indices'].append(i)
            
            # 6. 创建一个列表项目的元素索引集合，用于判断哪些列表包含相同的列表项
            list_item_sets = {}
            for i, list_info in enumerate(potential_lists):
                # 创建一个集合，包含该列表的所有列表项索引
                item_indices = set(list_info['item_indices'])
                list_item_sets[i] = item_indices
            
            # 7. 高级过滤 - 处理嵌套列表和重叠列表
            lists_to_remove = set()
            
            # 对列表进行优先级排序 - 首先根据深度（浅的优先），然后是列表项数量（多的优先）
            list_priorities = [(i, lst.get('depth', 0), -lst.get('item_count', 0)) 
                              for i, lst in enumerate(potential_lists)]
            list_priorities.sort(key=lambda x: (x[1], x[2]))  # 按深度升序，项目数量降序排序
            
            # 7.1 首先检查每个列表是否是另一个列表的子元素
            for i, list_info in enumerate(potential_lists):
                root_idx = list_info['root_index']
                
                # 检查该列表的根节点是否是其他列表的项
                for j, other_list in enumerate(potential_lists):
                    if i == j:
                        continue
                    
                    # 如果此列表的根是另一个列表的项目，标记此列表为移除
                    if root_idx in other_list['item_indices']:
                        lists_to_remove.add(i)
                        break
            
            # 7.2 检查列表之间的层次关系 - 如果列表A的根是列表B的祖先，则保留较大的列表
            for i, list_info in enumerate(potential_lists):
                if i in lists_to_remove:
                    continue
                    
                root_idx = list_info['root_index']
                ancestors = list_info.get('ancestor_indices', set())
                
                # 检查其他列表的根是否是此列表根的祖先
                for j, other_list in enumerate(potential_lists):
                    if i == j or j in lists_to_remove:
                        continue
                    
                    other_root_idx = other_list['root_index']
                    
                    # 如果此列表的根是另一个列表根的祖先，考虑哪个列表更重要
                    if other_root_idx in ancestors:
                        # 判断哪个列表更有价值 - 通常更大的列表更有价值
                        if list_info['item_count'] <= other_list['item_count']:
                            lists_to_remove.add(i)
                        else:
                            lists_to_remove.add(j)
                    
                    # 如果另一个列表的根是此列表根的祖先，也要考虑哪个更重要
                    elif root_idx in other_list.get('ancestor_indices', set()):
                        if list_info['item_count'] >= other_list['item_count']:
                            lists_to_remove.add(j)
                        else:
                            lists_to_remove.add(i)
            
            # 7.3 检查列表项目的重叠度 - 如果一个列表的大部分项目与另一个列表重叠，则移除较小的列表
            for i, j in [(i, j) for i in range(len(potential_lists)) for j in range(i+1, len(potential_lists))]:
                if i in lists_to_remove or j in lists_to_remove:
                    continue
                
                items_i = list_item_sets[i]
                items_j = list_item_sets[j]
                
                # 计算重叠率
                overlap = len(items_i.intersection(items_j))
                overlap_ratio_i = overlap / len(items_i) if items_i else 0
                overlap_ratio_j = overlap / len(items_j) if items_j else 0
                
                # 如果重叠率超过70%，移除较小的列表
                if overlap_ratio_i > 0.7 or overlap_ratio_j > 0.7:
                    # 比较列表大小和优先级
                    priority_i = list_priorities.index((i, potential_lists[i].get('depth', 0), -potential_lists[i].get('item_count', 0)))
                    priority_j = list_priorities.index((j, potential_lists[j].get('depth', 0), -potential_lists[j].get('item_count', 0)))
                    
                    if priority_i < priority_j:  # i的优先级更高
                        lists_to_remove.add(j)
                    else:
                        lists_to_remove.add(i)
            
            # 7.4 处理RecyclerView或ListView - 这些通常是主要列表容器
            # 如果存在RecyclerView/ListView类型的列表，其他在其内部的小列表可能是列表项的子组件
            recyclerview_lists = []
            
            for i, list_info in enumerate(potential_lists):
                if i in lists_to_remove:
                    continue
                
                root_class = list_info['root_element'].get('class', '')
                if ('RecyclerView' in root_class or 'ListView' in root_class) and list_info['item_count'] >= 3:
                    recyclerview_lists.append(i)
            
            # 如果找到RecyclerView列表，检查其他列表是否在其中
            for rv_idx in recyclerview_lists:
                rv_list = potential_lists[rv_idx]
                rv_items = set(rv_list['item_indices'])
                
                for i, list_info in enumerate(potential_lists):
                    if i == rv_idx or i in lists_to_remove:
                        continue
                    
                    # 判断该列表是否是RecyclerView中的子组件
                    root_idx = list_info['root_index']
                    is_subcomponent = False
                    
                    # 检查该列表的根是否是RecyclerView列表项的后代
                    for item_idx in rv_items:
                        # 检查是否有任何祖先关系
                        if root_idx == item_idx or (
                            item_idx in element_ancestors.get(root_idx, set()) or  # 列表项是根的祖先
                            root_idx in element_ancestors.get(item_idx, set())     # 根是列表项的祖先
                        ):
                            is_subcomponent = True
                            break
                    
                    # 如果是子组件，移除此列表
                    if is_subcomponent:
                        lists_to_remove.add(i)
                        
                        # 将其标记为RV列表的子列表
                        if i not in rv_list['child_list_indices']:
                            rv_list['child_list_indices'].append(i)
                            list_info['parent_list_index'] = rv_idx
            
            # 8. 从结果中过滤掉要移除的列表
            filtered_lists = [lst for i, lst in enumerate(potential_lists) if i not in lists_to_remove]
            
            # 9. 重新编号列表索引，因为我们已经移除了一些列表
            # 创建旧索引到新索引的映射
            index_map = {old_idx: new_idx for new_idx, old_idx in enumerate(
                [i for i in range(len(potential_lists)) if i not in lists_to_remove]
            )}
            
            # 更新所有引用
            for list_info in filtered_lists:
                # 更新父列表索引
                if list_info.get('parent_list_index') is not None:
                    old_parent_idx = list_info['parent_list_index']
                    if old_parent_idx in index_map:
                        list_info['parent_list_index'] = index_map[old_parent_idx]
                    else:
                        list_info['parent_list_index'] = None
                
                # 更新子列表索引
                new_child_indices = []
                for old_child_idx in list_info.get('child_list_indices', []):
                    if old_child_idx in index_map:
                        new_child_indices.append(index_map[old_child_idx])
                list_info['child_list_indices'] = new_child_indices
                
                # 移除祖先索引字段，这只是辅助字段
                if 'ancestor_indices' in list_info:
                    del list_info['ancestor_indices']
            
            # 10. 最终排序 - 按照列表项数量降序排列
            sorted_lists = sorted(filtered_lists, key=lambda x: -x.get('item_count', 0))
            
            # 更新结果
            result['success'] = True
            result['lists'] = sorted_lists
            result['list_count'] = len(sorted_lists)
            result['message'] = f'识别出 {len(sorted_lists)} 个列表结构'
            
            return result
                
        except Exception as e:
            result['message'] = f'识别列表结构时出错: {str(e)}'
            return result
    
    def __enter__(self):
        """支持with语句"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """with语句结束时断开连接"""
        pass
    
    def __del__(self):
        """析构时清理资源"""
        pass 