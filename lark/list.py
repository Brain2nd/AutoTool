import json
import uuid
import os
from datetime import datetime
import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *
from lark_oapi.api.bitable.v1.model.get_app_table_record_request import GetAppTableRecordRequest
from lark_oapi.api.bitable.v1.model.update_app_table_record_request import UpdateAppTableRecordRequest
from lark_oapi.api.bitable.v1.model.delete_app_table_record_request import DeleteAppTableRecordRequest
from lark_oapi.api.bitable.v1.model.search_app_table_record_request import SearchAppTableRecordRequest
from lark_oapi.api.bitable.v1.model.search_app_table_record_request_body import SearchAppTableRecordRequestBody
from lark_oapi.api.drive.v1 import *
from FeishuBitableAPI import FeishuBitableAPI

class LarkList:
    def __init__(self, url, app_id=None, app_secret=None, config_file=None, build_link_maps=True):
        """
        初始化LarkList类，通过URL获取飞书多维表格的信息
        
        Args:
            url (str): 飞书多维表格的URL
            app_id (str): 应用ID，可选
            app_secret (str): 应用密钥，可选
            config_file (str): 配置文件路径，可选
            build_link_maps (bool): 是否构建关联字段映射，默认True
        """
        self.api = FeishuBitableAPI()
        if app_id and app_secret:
            self.api_id = app_id
            self.api_secret = app_secret
        else:
            self.api_id = 'cli_a7569aeee9e2900d'
            self.api_secret = 'E8KtrwLDI7l0qrfqriAzCcMz2sJOiOzd'
        
        # 存储配置文件路径
        if config_file:
            self.config_file = config_file
        else:
            # 默认配置文件路径
            import os
            self.config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "feishu-config.ini")
        
        self.url = url
        self.info = self.api.GET_INFO_FROM_URL(url)
        self.app_token = self.info.get('app_token', '')
        self.table_id = self.info.get('table_id', '')
        self.view_id = self.info.get('view_id', '')
        
        # 创建lark client
        self.client = lark.Client.builder() \
            .app_id(self.api_id) \
            .app_secret(self.api_secret) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()
        
        # 加载基本映射文件
        self.map = self._load_map()
        
        # 初始化字段信息和关联字段映射
        self.fields_info = None
        self.link_field_maps = {}
        
        # 自动加载字段信息
        self._load_fields_info()
        
        # 只有在需要时才构建关联字段的映射
        if build_link_maps:
            self._build_link_field_maps()
    
    def _load_map(self):
        """
        加载映射文件
        
        Returns:
            dict: 映射关系字典，如果文件不存在则返回空字典
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        map_file_path = os.path.join(current_dir, "map", "map.json")
        try:
            if os.path.exists(map_file_path):
                with open(map_file_path, 'r', encoding='utf-8') as f:
                    map_data = json.load(f)
                print(f"已加载映射文件，共{len(map_data)}条映射关系")
                return map_data
            else:
                print(f"映射文件不存在: {map_file_path}")
                return {}
        except Exception as e:
            print(f"加载映射文件时出错: {str(e)}")
            return {}
    
    def _load_fields_info(self):
        """加载当前表格的字段信息"""
        try:
            fields_data = self.get_fields()
            if 'data' in fields_data and 'items' in fields_data['data']:
                self.fields_info = fields_data['data']['items']
                print(f"已加载字段信息，共{len(self.fields_info)}个字段")
            else:
                print("获取字段信息失败")
        except Exception as e:
            print(f"加载字段信息时出错: {str(e)}")
    
    def _build_link_field_maps(self):
        """构建关联字段的映射关系"""
        if not self.fields_info:
            return
            
        for field in self.fields_info:
            # 查找SingleLink类型的字段
            if field.get('ui_type') == 'SingleLink' and field.get('property'):
                field_name = field.get('field_name')
                link_table_id = field.get('property', {}).get('table_id')
                primary_field_id = field.get('property', {}).get('field_id', None)
                
                if link_table_id and field_name:
                    print(f"发现关联字段: {field_name}，关联表ID: {link_table_id}")
                    self._build_link_field_map(field_name, link_table_id, primary_field_id)
    
    def _build_link_field_map(self, field_name, link_table_id, primary_field_id=None):
        """
        构建单个关联字段的映射关系
        
        Args:
            field_name (str): 字段名称
            link_table_id (str): 关联表ID
            primary_field_id (str, optional): 主字段ID，如果不提供则自动查找
        """
        try:
            print(f"开始构建关联字段 '{field_name}' 的映射关系...")
            # 创建临时LarkList对象访问关联表，禁用映射构建避免递归
            temp_url = f"https://mcnmza4kafoj.feishu.cn/base/{self.app_token}?table={link_table_id}"
            temp_lark = self.__class__(temp_url, self.api_id, self.api_secret, self.config_file, build_link_maps=False)
            
            # 获取关联表的记录
            link_records = temp_lark.get_records()
            print(f"获取到关联表记录数据：{json.dumps(link_records, ensure_ascii=False)[:300]}...")
            
            # 获取关联表的字段信息
            temp_fields = temp_lark.get_fields()
            print(f"获取到关联表字段信息：{json.dumps(temp_fields, ensure_ascii=False)[:300]}...")
            
            # 尝试找到主字段ID（如果未指定）
            if not primary_field_id:
                if 'data' in temp_fields and 'items' in temp_fields['data']:
                    for field in temp_fields['data']['items']:
                        if field.get('is_primary', False):
                            primary_field_id = field.get('field_id')
                            print(f"找到关联表主字段ID: {primary_field_id}")
                            break
            
            # 如果仍未找到主字段，尝试查找"岗位名称"字段
            if not primary_field_id:
                if 'data' in temp_fields and 'items' in temp_fields['data']:
                    for field in temp_fields['data']['items']:
                        if field.get('field_name') in ['岗位名称', '职位名称', '名称']:
                            primary_field_id = field.get('field_id')
                            print(f"找到关联表名称字段ID: {primary_field_id}")
                            break
            
            if 'data' in link_records and 'items' in link_records['data']:
                field_map = {}
                
                # 构建名称到ID的映射
                for record in link_records['data']['items']:
                    record_id = record.get('record_id')
                    fields_data = record.get('fields', {})
                    
                    # 如果找到了主字段ID，优先使用
                    if primary_field_id and primary_field_id in fields_data:
                        record_name = fields_data.get(primary_field_id)
                    else:
                        # 尝试从字段数据中找到一个合适的名称字段
                        record_name = None
                        # 优先查找岗位名称字段
                        for field_key, field_value in fields_data.items():
                            if field_key == '岗位名称' or field_key == '职位名称' or field_key == '名称':
                                record_name = field_value
                                break
                        
                        # 如果没有找到专门的名称字段，使用任何非空字段
                        if not record_name:
                            for field_value in fields_data.values():
                                if field_value and isinstance(field_value, str):
                                    record_name = field_value
                                    break
                    
                    # 如果所有方法都失败，使用记录ID作为名称
                    if not record_name:
                        record_name = f"记录{record_id}"
                    
                    # 保存到映射字典
                    if isinstance(record_name, str):
                        field_map[record_name] = record_id
                        print(f"映射: {record_name} -> {record_id}")
                
                # 保存映射到内存中，不写入文件
                if field_map:
                    self.link_field_maps[field_name] = {
                        'table_id': link_table_id,
                        'primary_field_id': primary_field_id,
                        'map': field_map
                    }
                    
                    print(f"为字段 '{field_name}' 构建了{len(field_map)}条映射关系（仅内存）")
                    return True
                else:
                    print(f"警告: 未能为字段 '{field_name}' 构建任何映射关系")
                    return False
            else:
                print(f"警告: 未找到关联表的记录数据")
                return False
        except Exception as e:
            print(f"构建关联字段 '{field_name}' 的映射关系时出错: {str(e)}")
            return False
    
    def get_records(self):
        """
        获取当前表格的所有记录
        
        Returns:
            list: 记录列表
        """
        return self.api.LIST_RECORDS(app_token=self.app_token, table_id=self.table_id, config_file=self.config_file)
    
    def get_fields(self):
        """
        获取当前表格的所有字段
        
        Returns:
            dict: 字段信息
        """
        return self.api.LIST_FIELDS(app_token=self.app_token, table_id=self.table_id, view_id=self.view_id, config_file=self.config_file)
    
    def get_fields_detail(self):
        """
        获取当前表格所有字段的详细信息
        
        Returns:
            list: 包含字段详细信息的列表
        """
        fields_data = self.get_fields()
        if 'data' in fields_data and 'items' in fields_data['data']:
            field_items = fields_data['data']['items']
            fields_detail = []
            
            for field in field_items:
                field_info = {
                    "name": field['field_name'],
                    "id": field['field_id'],
                    "type": field['ui_type']
                }
                
                # 添加选项信息（如果有）
                if field.get('property') and 'options' in field.get('property', {}):
                    options = field['property']['options']
                    field_info["options"] = [{"name": opt['name'], "id": opt.get('id')} for opt in options]
                
                # 添加关联表信息（如果是SingleLink类型）
                if field['ui_type'] == 'SingleLink' and field.get('property'):
                    field_info["link_info"] = {
                        "table_id": field['property'].get('table_id'),
                        "field_id": field['property'].get('field_id')
                    }
                
                fields_detail.append(field_info)
            
            return fields_detail
        
        return []
    
    def get_linked_records(self, field_name, value, link_field_id=None):
        """
        获取关联表中的记录ID
        
        Args:
            field_name (str): 关联字段名称
            value (str): 要查找的值
            link_field_id (str, optional): 关联表中的字段ID
            
        Returns:
            str: 记录ID，未找到则返回None
        """
        # 获取所有字段信息
        fields_detail = self.get_fields_detail()
        
        # 找到对应的关联字段
        link_field = next((f for f in fields_detail if f['name'] == field_name), None)
        if not link_field or link_field['type'] != 'SingleLink':
            return None
        
        # 获取关联表信息
        link_table_id = link_field.get('link_info', {}).get('table_id')
        if not link_table_id:
            return None
        
        # 如果未指定关联表中的字段ID，则使用默认的字段ID
        if not link_field_id:
            link_field_id = link_field.get('link_info', {}).get('field_id')
        
        # 从关联表获取所有记录
        request = ListAppTableRecordRequest.builder() \
            .app_token(self.app_token) \
            .table_id(link_table_id) \
            .user_id_type("open_id") \
            .page_size(100) \
            .build()
        
        response = self.client.bitable.v1.app_table_record.list(request)
        
        if not response.success():
            lark.logger.error(
                f"获取关联表记录失败，错误码: {response.code}, 错误信息: {response.msg}, log_id: {response.get_log_id()}")
            return None
        
        # 在记录中查找对应的值
        items = response.data.items
        for item in items:
            fields = item.fields
            if str(fields.get(link_field_id)) == value:
                return item.record_id
        
        return None
    
    def get_table_id_by_name(self, table_name):
        """
        通过表格名称获取表格ID
        
        Args:
            table_name (str): 表格名称
            
        Returns:
            str: 表格ID
        """
        return self.api.GET_TABLE_ID(name=table_name, app_token=self.app_token, config_file=self.config_file)
    
    def switch_table(self, table_name):
        """
        切换到指定名称的表格
        
        Args:
            table_name (str): 表格名称
            
        Returns:
            bool: 切换是否成功
        """
        new_table_id = self.get_table_id_by_name(table_name)
        if new_table_id:
            self.table_id = new_table_id
            return True
        return False
    
    def get_info(self):
        """
        获取当前表格的完整信息
        
        Returns:
            dict: 包含app_token, table_id, view_id的字典
        """
        return {
            'app_token': self.app_token,
            'table_id': self.table_id,
            'view_id': self.view_id
        }
    
    def get_mapped_value(self, key):
        """
        根据键获取映射的值
        
        Args:
            key (str): 需要映射的键
            
        Returns:
            str: 映射后的值
            
        Raises:
            ValueError: 当键在映射中不存在时抛出异常
        """
        if key in self.map:
            return self.map[key]
        else:
            raise ValueError(f"映射中不存在键: {key}")
    
    def _convert_date_to_timestamp(self, date_value):
        """
        将各种格式的日期转换为毫秒级时间戳
        
        Args:
            date_value: 日期值，可以是字符串、datetime对象或时间戳
            
        Returns:
            int: 毫秒级时间戳
        """
        if isinstance(date_value, int):
            # 如果已经是时间戳，检查是否为毫秒级
            if len(str(date_value)) < 13:  # 秒级时间戳
                return date_value * 1000
            return date_value
        
        if isinstance(date_value, datetime):
            # 如果是datetime对象
            return int(date_value.timestamp() * 1000)
        
        # 尝试不同的日期格式
        date_formats = [
            "%Y/%m/%d", "%Y-%m-%d", "%Y年%m月%d日",
            "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"
        ]
        
        for date_format in date_formats:
            try:
                date_obj = datetime.strptime(date_value, date_format)
                return int(date_obj.timestamp() * 1000)
            except (ValueError, TypeError):
                continue
        
        # 如果所有格式都失败，返回当前时间
        return int(datetime.now().timestamp() * 1000)
    
    def upload_file(self, file_path):
        """
        上传文件到飞书云空间，自动识别文件类型
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            str: 文件token，上传失败则返回None
        """
        try:
            print(f"开始上传文件: {file_path}")
            
            # 获取文件名和大小
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            print(f"文件名: {file_name}, 文件大小: {file_size}字节")
            
            # 根据文件扩展名判断文件类型
            file_ext = os.path.splitext(file_name)[1].lower()
            print(f"文件扩展名: {file_ext}")
            
            # 图片类型扩展名列表
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            
            # 确定parent_type
            if file_ext in image_extensions:
                parent_type = "bitable_image"  # 图片类型
                print(f"识别为图片类型，使用parent_type: {parent_type}")
            else:
                parent_type = "bitable_file"   # 其他文件类型
                print(f"识别为普通文件类型，使用parent_type: {parent_type}")
            
            # 提供额外数据，指定表格ID
            extra_data = json.dumps({"bitablePerm": {"tableId": self.table_id}})
            print(f"构建额外数据: {extra_data}")
            
            # 打开文件
            print("开始打开文件...")
            with open(file_path, "rb") as file:
                print("文件已打开，开始构建请求...")
                # 构造请求对象
                request = UploadAllMediaRequest.builder() \
                    .request_body(UploadAllMediaRequestBody.builder()
                        .file_name(file_name)
                        .parent_type(parent_type)  # 根据文件类型自动选择
                        .parent_node(self.app_token)
                        .size(str(file_size))
                        .extra(extra_data)  # 添加额外数据
                        .file(file)
                        .build()) \
                    .build()
                
                print("请求已构建，开始发送请求...")
                # 发起请求
                response = self.client.drive.v1.media.upload_all(request)
                
                # 处理响应
                if not response.success():
                    lark.logger.error(
                        f"上传文件失败，错误码: {response.code}, 错误信息: {response.msg}, log_id: {response.get_log_id()}")
                    print(f"上传失败: 错误码={response.code}, 错误信息={response.msg}")
                    return None
                
                print(f"上传成功，获取到文件token: {response.data.file_token}")
                # 返回文件token
                return response.data.file_token
        except Exception as e:
            lark.logger.error(f"上传文件异常: {str(e)}")
            print(f"上传过程中发生异常: {str(e)}")
            return None
    
    def _get_option_id(self, field_name, option_name):
        """
        根据字段名和选项名称获取选项ID
        
        Args:
            field_name (str): 字段名
            option_name (str): 选项名称
            
        Returns:
            str: 选项ID，找不到则返回None
        """
        if not self.fields_info:
            return None
            
        # 查找对应字段
        for field in self.fields_info:
            if field.get('field_name') == field_name:
                # 检查是否有选项
                if field.get('property') and 'options' in field.get('property', {}):
                    options = field['property']['options']
                    for option in options:
                        if option.get('name') == option_name:
                            return option.get('id')
                break
        return None

    def _process_select_field(self, field_name, value, field_type):
        """
        处理单选/多选字段的值，将选项名称转换为选项ID
        
        Args:
            field_name (str): 字段名
            value: 原始值，可以是字符串或列表
            field_type (str): 字段类型，'SingleSelect' 或 'MultiSelect'
            
        Returns:
            list: 选项ID列表
        """
        # 处理单个值或列表值
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, list):
            values = value
        else:
            values = [str(value)]
        
        option_ids = []
        for val in values:
            str_val = str(val).strip()
            
            # 先尝试使用基本映射转换值
            try:
                mapped_val = self.get_mapped_value(str_val)
                print(f"基本映射: {str_val} -> {mapped_val}")
                str_val = mapped_val
            except ValueError:
                # 如果在基本映射中找不到，就使用原始值
                pass
            
            # 获取选项ID
            option_id = self._get_option_id(field_name, str_val)
            if option_id:
                option_ids.append(option_id)
                print(f"处理选择字段 '{field_name}': {str_val} -> {option_id}")
            else:
                print(f"警告: 在字段 '{field_name}' 中找不到选项 '{str_val}' 的ID")
        
        return option_ids
    
    def _process_link_field(self, field_name, value):
        """
        处理关联字段的值，将名称转换为ID
        
        Args:
            field_name (str): 字段名
            value: 原始值，可以是字符串或列表
            
        Returns:
            list: 记录ID列表，如果转换失败则返回None
        """
        # 处理单个值或列表值
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, list):
            values = value
        else:
            values = [str(value)]
        
        # 先尝试使用基本映射转换值
        mapped_values = []
        for val in values:
            str_val = str(val)
            # 尝试使用基本映射
            try:
                mapped_val = self.get_mapped_value(str_val)
                print(f"基本映射: {str_val} -> {mapped_val}")
                mapped_values.append(mapped_val)
            except ValueError:
                # 如果在基本映射中找不到，就使用原始值
                print(f"在基本映射中未找到 '{str_val}'，使用原始值")
                mapped_values.append(str_val)
        
        # 检查是否有该字段的映射信息
        if field_name not in self.link_field_maps:
            # 直接尝试获取关联字段信息并构建映射
            fields_detail = self.get_fields_detail()
            link_field = next((f for f in fields_detail if f['name'] == field_name), None)
            
            if link_field and link_field.get('type') == 'SingleLink' and link_field.get('link_info'):
                link_table_id = link_field['link_info']['table_id']
                primary_field_id = link_field['link_info'].get('field_id')
                print(f"尝试构建关联字段 '{field_name}' 的映射关系")
                self._build_link_field_map(field_name, link_table_id, primary_field_id)
            else:
                print(f"无法找到关联字段 '{field_name}' 的配置信息")
        
        # 获取映射
        field_map = self.link_field_maps.get(field_name, {}).get('map', {})
        
        # 转换为ID
        record_ids = []
        for mapped_val in mapped_values:
            # 直接查找映射
            if mapped_val in field_map:
                record_id = field_map[mapped_val]
                record_ids.append(record_id)
                print(f"找到关联记录ID: {mapped_val} -> {record_id}")
            else:
                print(f"警告: 找不到 '{mapped_val}' 的关联记录ID")
                
                # 尝试部分匹配（针对岗位名称可能有前缀或后缀的情况）
                matched = False
                for key, value in field_map.items():
                    if mapped_val in key or key in mapped_val:
                        record_ids.append(value)
                        print(f"使用部分匹配: {mapped_val} 匹配到 {key} -> {value}")
                        matched = True
                        break
                
                if not matched:
                    print(f"无法找到 '{mapped_val}' 的匹配，尝试重建映射...")
                    # 尝试重建映射
                    fields_detail = self.get_fields_detail()
                    link_field = next((f for f in fields_detail if f['name'] == field_name), None)
                    
                    if link_field and link_field.get('type') == 'SingleLink' and link_field.get('link_info'):
                        link_table_id = link_field['link_info']['table_id']
                        primary_field_id = link_field['link_info'].get('field_id')
                        if self._build_link_field_map(field_name, link_table_id, primary_field_id):
                            # 重新获取映射
                            field_map = self.link_field_maps.get(field_name, {}).get('map', {})
                            # 再次尝试匹配
                            for key, value in field_map.items():
                                if mapped_val in key or key in mapped_val:
                                    record_ids.append(value)
                                    print(f"重建映射后匹配: {mapped_val} 匹配到 {key} -> {value}")
                                    matched = True
                                    break
        
        return record_ids if record_ids else None
    
    def add_record(self, fields):
        """
        向当前表格添加一条记录
        
        Args:
            fields (dict): 字段名和值的字典，例如 {"文本": "测试", "日期": "2023/09/30", "附件": "/path/to/file.jpg"}
            
        Returns:
            dict: 添加记录的响应结果
        """
        # 处理字段
        processed_fields = {}
        
        # 获取字段类型信息
        field_types = {}
        for field in self.fields_info if self.fields_info else []:
            field_types[field.get('field_name')] = field.get('ui_type')
        
        for key, value in fields.items():
            # 获取字段类型
            field_type = field_types.get(key)
            
            # 处理日期类型字段
            if field_type == 'DateTime' or (key.lower().find('日期') >= 0 or key.lower().find('time') >= 0 or key.lower().find('date') >= 0):
                processed_fields[key] = self._convert_date_to_timestamp(value)
            
            # 处理数字类型字段
            elif field_type == 'Number':
                try:
                    # 尝试将值转换为数字
                    if isinstance(value, str):
                        # 移除可能的货币符号和逗号
                        clean_value = value.replace('$', '').replace(',', '').strip()
                        processed_fields[key] = float(clean_value)
                    else:
                        processed_fields[key] = float(value)
                    print(f"处理数字字段 '{key}': {value} -> {processed_fields[key]}")
                except (ValueError, TypeError) as e:
                    print(f"警告: 数字字段 '{key}' 转换失败: {value} -> {e}")
                    processed_fields[key] = 0  # 使用默认值
            
            # 处理关联字段
            elif field_type == 'SingleLink':
                record_ids = self._process_link_field(key, value)
                if record_ids:
                    processed_fields[key] = record_ids
                    print(f"处理关联字段 '{key}': {value} -> {record_ids}")
                else:
                    print(f"警告: 跳过关联字段 '{key}'，找不到对应的记录ID")
            
            # 处理单选/多选类型字段
            elif field_type in ['SingleSelect', 'MultiSelect']:
                # 飞书API应该直接接受选项名称，而不是选项ID
                if isinstance(value, list):
                    processed_fields[key] = value
                    print(f"处理多选字段 '{key}': {value} -> {value}")
                else:
                    # 单选字段直接传递选项名称
                    processed_fields[key] = str(value)
                    print(f"处理单选字段 '{key}': {value} -> {str(value)}")
            
            # 处理列表类型字段
            elif isinstance(value, list):
                processed_fields[key] = value
            
            # 处理文件上传
            elif isinstance(value, str) and os.path.exists(value) and os.path.isfile(value):
                file_token = self.upload_file(value)
                if file_token:
                    processed_fields[key] = [{"file_token": file_token, "name": os.path.basename(value)}]
                else:
                    lark.logger.warning(f"文件 {value} 上传失败，跳过该字段")
                    print(f"警告: 文件 {value} 上传失败，跳过该字段")
            
            # 其他类型直接处理
            else:
                processed_fields[key] = value
        
        # 生成唯一的client_token
        client_token = str(uuid.uuid4())
        
        print('===============================================')
        print("最终要提交的字段:")
        print(processed_fields)
        print('===============================================')
        
        # 构造请求对象
        request = CreateAppTableRecordRequest.builder() \
            .app_token(self.app_token) \
            .table_id(self.table_id) \
            .user_id_type("open_id") \
            .client_token(client_token) \
            .request_body(AppTableRecord.builder()
                .fields(processed_fields)
                .build()) \
            .build()
        
        # 发起请求
        response = self.client.bitable.v1.app_table_record.create(request)
        
        # 处理响应
        if not response.success():
            lark.logger.error(
                f"添加记录失败，错误码: {response.code}, 错误信息: {response.msg}, log_id: {response.get_log_id()}")
            return {"success": False, "error": response.msg}
        
        return {"success": True, "data": json.loads(lark.JSON.marshal(response.data))}

    def get_record(self, record_id):
        """
        根据记录ID获取单条记录
        
        Args:
            record_id (str): 记录ID
            
        Returns:
            dict: 记录数据或错误信息
        """
        try:
            # 构造请求对象
            request = GetAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .record_id(record_id) \
                .user_id_type("open_id") \
                .build()
            
            # 发起请求
            response = self.client.bitable.v1.app_table_record.get(request)
            
            # 处理响应
            if not response.success():
                lark.logger.error(
                    f"获取记录失败，错误码: {response.code}, 错误信息: {response.msg}, log_id: {response.get_log_id()}")
                return {"success": False, "error": response.msg}
            
            return {"success": True, "data": json.loads(lark.JSON.marshal(response.data))}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_record(self, record_id, fields):
        """
        更新指定记录的字段
        
        Args:
            record_id (str): 记录ID
            fields (dict): 要更新的字段数据
            
        Returns:
            dict: 更新结果
        """
        # 处理字段（复用add_record的字段处理逻辑）
        processed_fields = {}
        
        # 获取字段类型信息
        field_types = {}
        for field in self.fields_info if self.fields_info else []:
            field_types[field.get('field_name')] = field.get('ui_type')
        
        for key, value in fields.items():
            # 获取字段类型
            field_type = field_types.get(key)
            
            # 处理日期类型字段
            if field_type == 'DateTime' or (key.lower().find('日期') >= 0 or key.lower().find('time') >= 0 or key.lower().find('date') >= 0):
                processed_fields[key] = self._convert_date_to_timestamp(value)
            
            # 处理数字类型字段
            elif field_type == 'Number':
                try:
                    # 尝试将值转换为数字
                    if isinstance(value, str):
                        # 移除可能的货币符号和逗号
                        clean_value = value.replace('$', '').replace(',', '').strip()
                        processed_fields[key] = float(clean_value)
                    else:
                        processed_fields[key] = float(value)
                    print(f"处理数字字段 '{key}': {value} -> {processed_fields[key]}")
                except (ValueError, TypeError) as e:
                    print(f"警告: 数字字段 '{key}' 转换失败: {value} -> {e}")
                    processed_fields[key] = 0  # 使用默认值
            
            # 处理关联字段
            elif field_type == 'SingleLink':
                record_ids = self._process_link_field(key, value)
                if record_ids:
                    processed_fields[key] = record_ids
                    print(f"处理关联字段 '{key}': {value} -> {record_ids}")
                else:
                    print(f"警告: 跳过关联字段 '{key}'，找不到对应的记录ID")
            
            # 处理单选/多选类型字段
            elif field_type in ['SingleSelect', 'MultiSelect']:
                # 飞书API应该直接接受选项名称，而不是选项ID
                if isinstance(value, list):
                    processed_fields[key] = value
                    print(f"处理多选字段 '{key}': {value} -> {value}")
                else:
                    # 单选字段直接传递选项名称
                    processed_fields[key] = str(value)
                    print(f"处理单选字段 '{key}': {value} -> {str(value)}")
            
            # 处理列表类型字段
            elif isinstance(value, list):
                processed_fields[key] = value
            
            # 处理文件上传
            elif isinstance(value, str) and os.path.exists(value) and os.path.isfile(value):
                file_token = self.upload_file(value)
                if file_token:
                    processed_fields[key] = [{"file_token": file_token, "name": os.path.basename(value)}]
                else:
                    lark.logger.warning(f"文件 {value} 上传失败，跳过该字段")
                    print(f"警告: 文件 {value} 上传失败，跳过该字段")
            
            # 其他类型直接处理
            else:
                processed_fields[key] = value
        
        print('===============================================')
        print(f"更新记录 {record_id} 的字段:")
        print(processed_fields)
        print('===============================================')
        
        try:
            # 构造请求对象
            request = UpdateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .record_id(record_id) \
                .user_id_type("open_id") \
                .request_body(AppTableRecord.builder()
                    .fields(processed_fields)
                    .build()) \
                .build()
            
            # 发起请求
            response = self.client.bitable.v1.app_table_record.update(request)
            
            # 处理响应
            if not response.success():
                lark.logger.error(
                    f"更新记录失败，错误码: {response.code}, 错误信息: {response.msg}, log_id: {response.get_log_id()}")
                return {"success": False, "error": response.msg}
            
            return {"success": True, "data": json.loads(lark.JSON.marshal(response.data))}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_record(self, record_id):
        """
        删除指定记录
        
        Args:
            record_id (str): 记录ID
            
        Returns:
            dict: 删除结果
        """
        try:
            # 构造请求对象
            request = DeleteAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .record_id(record_id) \
                .build()
            
            # 发起请求
            response = self.client.bitable.v1.app_table_record.delete(request)
            
            # 处理响应
            if not response.success():
                lark.logger.error(
                    f"删除记录失败，错误码: {response.code}, 错误信息: {response.msg}, log_id: {response.get_log_id()}")
                return {"success": False, "error": response.msg}
            
            return {"success": True, "message": f"记录 {record_id} 删除成功"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_records(self, filter_condition=None, sort_condition=None, page_size=20):
        """
        根据条件搜索记录
        
        Args:
            filter_condition (str): 过滤条件，例如 'AND(CurrentValue.[字段名]="值")'
            sort_condition (list): 排序条件，例如 [{"field_name": "字段名", "desc": False}]
            page_size (int): 每页记录数
            
        Returns:
            dict: 搜索结果
        """
        try:
            # 构造请求对象
            request_builder = SearchAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(self.table_id) \
                .user_id_type("open_id") \
                .page_size(page_size)
            
            # 添加过滤条件
            if filter_condition:
                request_builder.request_body(
                    SearchAppTableRecordRequestBody.builder()
                    .filter(filter_condition)
                    .build()
                )
            
            request = request_builder.build()
            
            # 发起请求
            response = self.client.bitable.v1.app_table_record.search(request)
            
            # 处理响应
            if not response.success():
                lark.logger.error(
                    f"搜索记录失败，错误码: {response.code}, 错误信息: {response.msg}, log_id: {response.get_log_id()}")
                return {"success": False, "error": response.msg}
            
            return {"success": True, "data": json.loads(lark.JSON.marshal(response.data))}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
