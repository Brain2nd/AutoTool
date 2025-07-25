#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import configparser
import requests
import json
from FeishuBitableAPI import FeishuBitableAPI
from .auto_login import GET_LOGIN_CODE_AUTO

class FeishuBitable:
    """
    飞书多维表格API封装类
    """
    def __init__(self, config_file=None, auto_login=True):
        """
        初始化飞书多维表格类
        
        Args:
            config_file: 配置文件路径，默认为None
            auto_login: 是否启用自动登录，默认为True
        """
        self.config_file = config_file or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "feishu-config.ini")
        self.config = self._load_config()
        self.api = FeishuBitableAPI()
        self.auto_login = auto_login
        
        # 初始化时直接刷新所有token
        print("已加载配置文件: {self.config_file}")

        if auto_login:
            print("初始化时刷新所有token...")
            self.refresh_tokens()
    
    def _detect_task_port(self):
        """
        检测当前任务应该使用的Chrome调试端口
        
        Returns:
            检测到的端口号，如果无法检测则返回None
        """
        import os
        import inspect
        
        try:
            current_dir = os.getcwd()
            
            # 检查调用栈中的脚本路径
            calling_script = ""
            for frame_info in inspect.stack():
                filename = frame_info.filename
                if any(task in filename for task in ['influencertool', 'hr', 'larkbusiness', 'sca', 'macwx', 'asyncbusiness']):
                    calling_script = filename
                    break
            
            print(f"🔍 FeishuBitable端口检测 - 调用脚本: {calling_script}")
            print(f"🔍 FeishuBitable端口检测 - 当前目录: {current_dir}")
            
            # 根据调用脚本路径和当前目录确定端口
            if 'influencertool' in calling_script or 'influencertool' in current_dir:
                return 9223  # influencertool端口
            elif 'hr' in calling_script or 'hr' in current_dir:
                return 9224  # hr端口
            elif 'larkbusiness' in calling_script or 'larkbusiness' in current_dir:
                return 9222  # larkbusiness端口
            elif 'sca' in calling_script or 'sca' in current_dir:
                return 9225  # sca端口
            elif 'macwx' in calling_script or 'macwx' in current_dir:
                return 9226  # macwx端口
            elif 'asyncbusiness' in calling_script or 'asyncbusiness' in current_dir:
                return 9227  # asyncbusiness端口
            else:
                return None  # 无法检测，让系统使用默认逻辑
                
        except Exception as e:
            print(f"⚠️ 端口检测失败: {e}")
            return None
    
    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
        
        config = configparser.ConfigParser()
        try:
            config.read(self.config_file, encoding='utf-8')
            print(f"已加载配置文件: {self.config_file}")
        except Exception as e:
            print(f"警告: 读取配置文件时出错: {e}")
            # 重新初始化配置
            config = configparser.ConfigParser()
        
        # 确保TOKEN section存在
        if 'TOKEN' not in config:
            print("警告: 配置文件中缺少TOKEN section，正在创建...")
            config.add_section('TOKEN')
            # 保存修改后的配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            print("已创建TOKEN section并保存配置文件")
        
        return config
    
    def _update_config_token(self, token_name, token_value):
        """
        更新配置文件中的单个token
        
        Args:
            token_name: token名称
            token_value: token值
        """
        # 确保TOKEN section存在
        if 'TOKEN' not in self.config:
            print("警告: TOKEN section不存在，正在创建...")
            self.config.add_section('TOKEN')
        
        self.config['TOKEN'][token_name] = token_value
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            print(f"已更新配置文件中的{token_name}")
        except Exception as e:
            print(f"警告: 保存TOKEN配置时出错: {e}")
            # 如果保存失败，尝试重新加载配置
            self.config = self._load_config()
    
    def _update_config_field(self, section, field_name, field_value):
        """
        更新配置文件中的任意字段
        
        Args:
            section: 配置节名称
            field_name: 字段名称
            field_value: 字段值
        """
        # 确保section存在
        if section not in self.config:
            print(f"警告: {section} section不存在，正在创建...")
            self.config.add_section(section)
        
        self.config[section][field_name] = field_value
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            print(f"已更新配置文件中的[{section}]{field_name}")
        except Exception as e:
            print(f"警告: 保存配置文件时出错: {e}")
            # 如果保存失败，尝试重新加载配置
            self.config = self._load_config()
    
    def _get_proxies(self):
        # 暂时禁用代理
        original_proxies = {
            'http': os.environ.get('http_proxy'),
            'https': os.environ.get('https_proxy')
        }
        os.environ['http_proxy'] = ''
        os.environ['https_proxy'] = ''
        return original_proxies

    def _restore_proxies(self, proxies):
        # 恢复代理
        if proxies['http']:
            os.environ['http_proxy'] = proxies['http']
        else:
            os.environ.pop('http_proxy', None)
            
        if proxies['https'] :
            os.environ['https_proxy'] = proxies['https']
        else:
            os.environ.pop('https_proxy', None)

    def get_tenant_access_token(self):
        return self.tenant_access_token

    def refresh_tokens(self):
        """
        刷新所有token，每获取一个就立即更新配置文件
        """
        print("正在获取tenant_access_token...")
        original_proxies = self._get_proxies()
        try:
            self.tenant_access_token = self.api.GET_TENANT_ACCESS_TOKEN(config_file=self.config_file)
        finally:
            self._restore_proxies(original_proxies)
            
        if self.tenant_access_token:
            print("tenant_access_token 获取成功")
        else:
            print("获取tenant_access_token失败，无法继续初始化")
            raise Exception("获取tenant_access_token失败，可能是网络问题")
            
        print(f"获取到tenant_access_token: {self.tenant_access_token}")
        # 立即更新配置
        self._update_config_token('tenant_access_token', self.tenant_access_token)
        
        print("正在获取app_access_token...")
        self.app_access_token = self.api.GET_APP_ACCESS_TOKEN(config_file=self.config_file)
        print(f"获取到app_access_token: {self.app_access_token}")
        # 立即更新配置
        self._update_config_token('app_access_token', self.app_access_token)
        
        print("正在获取login_code...")
        # 根据 auto_login 参数决定使用哪种方式获取 login_code
        if self.auto_login:
            print("使用自动登录方式...")
            # 自动检测当前任务应该使用的端口
            preferred_port = self._detect_task_port()
            if preferred_port:
                print(f"检测到任务端口: {preferred_port}")
            self.login_code = GET_LOGIN_CODE_AUTO(config_file=self.config_file, preferred_port=preferred_port)
        else:
            self.login_code = self.api.GET_LOGIN_CODE(config_file=self.config_file)
        
        # 检查login_code是否获取成功
        if not self.login_code:
            print("获取login_code失败，无法继续初始化")
            raise Exception("获取login_code失败，可能是自动登录失败或网络问题")
            
        print(f"获取到login_code: {self.login_code}")
        # 立即更新配置
        self._update_config_token('login_code', self.login_code)
        
        print("正在获取user_access_token和refresh_token...")
        user_token_result = self.api.GET_USER_ACCESS_TOKEN(login_code=self.login_code, config_file=self.config_file)
        print(user_token_result)
        self.user_access_token = user_token_result[0]
        self.refresh_token = user_token_result[1]
        print(f"获取到user_access_token: {self.user_access_token}")
        print(f"获取到refresh_token: {self.refresh_token}")
        # 立即更新配置
        self._update_config_token('user_access_token', self.user_access_token)
        self._update_config_token('refresh_token', self.refresh_token)
        
        return {
            "tenant_access_token": self.tenant_access_token,
            "app_access_token": self.app_access_token,
            "login_code": self.login_code,
            "user_access_token": self.user_access_token,
            "refresh_token": self.refresh_token
        }
    
    def get_info(self):
        """
        获取当前的token信息
        
        Returns:
            dict: 包含所有token的字典
        """
        return {
            "tenant_access_token": self.tenant_access_token,
            "app_access_token": self.app_access_token,
            "login_code": self.login_code,
            "user_access_token": self.user_access_token,
            "refresh_token": self.refresh_token
        }