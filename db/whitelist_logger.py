#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
白名单操作专用日志记录器

功能：
- 记录所有白名单相关操作
- 提供详细的操作追踪
- 便于问题诊断和调试
- 独立的日志文件存储
"""

import os
import logging
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import threading

class WhitelistLogger:
    """白名单操作专用日志记录器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化日志记录器"""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        
        # 设置日志目录
        self.log_dir = Path(__file__).parent.parent.parent / "logs" / "whitelist"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志文件路径
        self.log_file = self.log_dir / f"whitelist_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 配置日志记录器
        self.logger = logging.getLogger('whitelist_operations')
        self.logger.setLevel(logging.DEBUG)
        
        # 清除现有的处理器
        self.logger.handlers.clear()
        
        # 文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 防止重复记录
        self.logger.propagate = False
        
        self.info("白名单日志记录器初始化完成", extra_data={
            "log_file": str(self.log_file),
            "log_dir": str(self.log_dir)
        })
    
    def _format_extra_data(self, extra_data: Dict[str, Any]) -> str:
        """格式化额外数据"""
        if not extra_data:
            return ""
        
        try:
            formatted_parts = []
            for key, value in extra_data.items():
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, ensure_ascii=False, indent=2)
                else:
                    value_str = str(value)
                formatted_parts.append(f"{key}: {value_str}")
            
            return " | " + " | ".join(formatted_parts)
        except Exception as e:
            return f" | extra_data_error: {str(e)}"
    
    def debug(self, message: str, extra_data: Dict[str, Any] = None):
        """记录调试信息"""
        full_message = message + self._format_extra_data(extra_data or {})
        self.logger.debug(full_message)
    
    def info(self, message: str, extra_data: Dict[str, Any] = None):
        """记录信息"""
        full_message = message + self._format_extra_data(extra_data or {})
        self.logger.info(full_message)
    
    def warning(self, message: str, extra_data: Dict[str, Any] = None):
        """记录警告"""
        full_message = message + self._format_extra_data(extra_data or {})
        self.logger.warning(full_message)
    
    def error(self, message: str, extra_data: Dict[str, Any] = None, exception: Exception = None):
        """记录错误"""
        full_message = message + self._format_extra_data(extra_data or {})
        
        if exception:
            full_message += f" | exception: {str(exception)} | traceback: {traceback.format_exc()}"
        
        self.logger.error(full_message)
    
    def operation_start(self, operation: str, module: str = None, extra_data: Dict[str, Any] = None):
        """记录操作开始"""
        data = {"operation": operation}
        if module:
            data["module"] = module
        if extra_data:
            data.update(extra_data)
        
        self.info(f"🚀 开始操作: {operation}", data)
    
    def operation_success(self, operation: str, module: str = None, extra_data: Dict[str, Any] = None):
        """记录操作成功"""
        data = {"operation": operation, "status": "success"}
        if module:
            data["module"] = module
        if extra_data:
            data.update(extra_data)
        
        self.info(f"✅ 操作成功: {operation}", data)
    
    def operation_failure(self, operation: str, error_msg: str, module: str = None, 
                         extra_data: Dict[str, Any] = None, exception: Exception = None):
        """记录操作失败"""
        data = {"operation": operation, "status": "failure", "error": error_msg}
        if module:
            data["module"] = module
        if extra_data:
            data.update(extra_data)
        
        self.error(f"❌ 操作失败: {operation} - {error_msg}", data, exception)
    
    def database_connect_attempt(self, attempt: int, max_attempts: int):
        """记录数据库连接尝试"""
        self.info(f"🔗 数据库连接尝试", {
            "attempt": attempt,
            "max_attempts": max_attempts
        })
    
    def database_connect_success(self, attempt: int):
        """记录数据库连接成功"""
        self.info(f"✅ 数据库连接成功", {"attempt": attempt})
    
    def database_connect_failure(self, attempt: int, error_msg: str, exception: Exception = None):
        """记录数据库连接失败"""
        data = {
            "attempt": attempt,
            "error": error_msg
        }
        
        if exception:
            self.error(f"❌ 数据库连接失败", data, exception)
        else:
            self.warning(f"❌ 数据库连接失败", data)
    
    def whitelist_load_start(self, source: str, module: str):
        """记录白名单加载开始"""
        self.info(f"📋 开始加载白名单", {
            "source": source,  # "database" 或 "file"
            "module": module
        })
    
    def whitelist_load_success(self, source: str, module: str, count: int, items: List[str] = None):
        """记录白名单加载成功"""
        data = {
            "source": source,
            "module": module,
            "count": count
        }
        if items:
            data["items"] = items
        
        self.info(f"✅ 白名单加载成功", data)
    
    def whitelist_load_failure(self, source: str, module: str, error_msg: str, exception: Exception = None):
        """记录白名单加载失败"""
        self.error(f"❌ 白名单加载失败", {
            "source": source,
            "module": module,
            "error": error_msg
        }, exception)
    
    def whitelist_save_start(self, target: str, module: str, count: int, items: List[str] = None):
        """记录白名单保存开始"""
        data = {
            "target": target,  # "database" 或 "file"
            "module": module,
            "count": count
        }
        if items:
            data["items"] = items
        
        self.info(f"💾 开始保存白名单", data)
    
    def whitelist_save_success(self, target: str, module: str, count: int):
        """记录白名单保存成功"""
        self.info(f"✅ 白名单保存成功", {
            "target": target,
            "module": module,
            "count": count
        })
    
    def whitelist_save_failure(self, target: str, module: str, error_msg: str, exception: Exception = None):
        """记录白名单保存失败"""
        self.error(f"❌ 白名单保存失败", {
            "target": target,
            "module": module,
            "error": error_msg
        }, exception)
    
    def whitelist_sync_start(self, from_source: str, to_target: str, module: str):
        """记录白名单同步开始"""
        self.info(f"🔄 开始同步白名单", {
            "from": from_source,
            "to": to_target,
            "module": module
        })
    
    def whitelist_sync_success(self, from_source: str, to_target: str, module: str, count: int):
        """记录白名单同步成功"""
        self.info(f"✅ 白名单同步成功", {
            "from": from_source,
            "to": to_target,
            "module": module,
            "count": count
        })
    
    def whitelist_sync_failure(self, from_source: str, to_target: str, module: str, 
                              error_msg: str, exception: Exception = None):
        """记录白名单同步失败"""
        self.error(f"❌ 白名单同步失败", {
            "from": from_source,
            "to": to_target,
            "module": module,
            "error": error_msg
        }, exception)
    
    def web_request_start(self, endpoint: str, method: str, module: str, client_ip: str = None):
        """记录Web请求开始"""
        data = {
            "endpoint": endpoint,
            "method": method,
            "module": module
        }
        if client_ip:
            data["client_ip"] = client_ip
        
        self.info(f"🌐 Web请求开始", data)
    
    def web_request_success(self, endpoint: str, method: str, module: str, response_data: Dict = None):
        """记录Web请求成功"""
        data = {
            "endpoint": endpoint,
            "method": method,
            "module": module
        }
        if response_data:
            data["response"] = response_data
        
        self.info(f"✅ Web请求成功", data)
    
    def web_request_failure(self, endpoint: str, method: str, module: str, 
                           error_msg: str, exception: Exception = None):
        """记录Web请求失败"""
        self.error(f"❌ Web请求失败", {
            "endpoint": endpoint,
            "method": method,
            "module": module,
            "error": error_msg
        }, exception)
    
    def data_verification(self, operation: str, expected: Any, actual: Any, passed: bool):
        """记录数据验证"""
        level = "info" if passed else "warning"
        message = f"🔍 数据验证: {operation}"
        
        data = {
            "operation": operation,
            "expected": expected,
            "actual": actual,
            "passed": passed
        }
        
        if passed:
            self.info(f"✅ {message} - 通过", data)
        else:
            self.warning(f"⚠️ {message} - 失败", data)
    
    def get_log_file_path(self) -> str:
        """获取当前日志文件路径"""
        return str(self.log_file)
    
    def get_recent_logs(self, lines: int = 100) -> List[str]:
        """获取最近的日志行"""
        try:
            if not self.log_file.exists():
                return []
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            self.error(f"读取日志文件失败: {str(e)}", exception=e)
            return []


# 全局日志记录器实例
whitelist_logger = WhitelistLogger()


# 便捷函数
def log_operation_start(operation: str, module: str = None, **kwargs):
    """便捷函数：记录操作开始"""
    whitelist_logger.operation_start(operation, module, kwargs)

def log_operation_success(operation: str, module: str = None, **kwargs):
    """便捷函数：记录操作成功"""
    whitelist_logger.operation_success(operation, module, kwargs)

def log_operation_failure(operation: str, error_msg: str, module: str = None, 
                         exception: Exception = None, **kwargs):
    """便捷函数：记录操作失败"""
    whitelist_logger.operation_failure(operation, error_msg, module, kwargs, exception)

def log_database_operation(operation_type: str, success: bool, **kwargs):
    """便捷函数：记录数据库操作"""
    if success:
        whitelist_logger.operation_success(f"database_{operation_type}", "larkbusiness", kwargs)
    else:
        whitelist_logger.operation_failure(f"database_{operation_type}", 
                                          kwargs.get('error', '未知错误'), 
                                          "larkbusiness", 
                                          kwargs.get('exception'),
                                          kwargs)

def log_web_operation(operation_type: str, success: bool, **kwargs):
    """便捷函数：记录Web操作"""
    if success:
        whitelist_logger.operation_success(f"web_{operation_type}", "lark", kwargs)
    else:
        whitelist_logger.operation_failure(f"web_{operation_type}", 
                                          kwargs.get('error', '未知错误'), 
                                          "lark", 
                                          kwargs.get('exception'),
                                          kwargs)


if __name__ == "__main__":
    # 测试日志记录器
    logger = WhitelistLogger()
    
    logger.info("测试白名单日志记录器")
    logger.operation_start("test_operation", "larkbusiness", {"test": "data"})
    logger.operation_success("test_operation", "larkbusiness", {"result": "success"})
    
    print(f"日志文件位置: {logger.get_log_file_path()}")
    print("最近5行日志:")
    for line in logger.get_recent_logs(5):
        print(line.strip()) 