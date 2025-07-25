#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
白名单日志记录器测试脚本

用于验证白名单日志记录器的各种功能
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from ..db.whitelist_logger import whitelist_logger

def test_basic_logging():
    """测试基本日志功能"""
    print("🧪 测试基本日志功能...")
    
    whitelist_logger.info("测试信息日志")
    whitelist_logger.warning("测试警告日志")
    whitelist_logger.error("测试错误日志")
    
    print("✅ 基本日志功能测试完成")

def test_operation_logging():
    """测试操作日志功能"""
    print("\n🧪 测试操作日志功能...")
    
    # 测试操作开始/成功/失败
    whitelist_logger.operation_start("test_operation", "larkbusiness", {"test_data": "value"})
    whitelist_logger.operation_success("test_operation", "larkbusiness", {"result": "success"})
    whitelist_logger.operation_failure("test_operation_fail", "测试错误", "larkbusiness", None, {"extra": "data"})
    
    print("✅ 操作日志功能测试完成")

def test_database_logging():
    """测试数据库连接日志功能"""
    print("\n🧪 测试数据库连接日志功能...")
    
    # 模拟数据库连接尝试
    whitelist_logger.database_connect_attempt(1, 3)
    whitelist_logger.database_connect_failure(1, "连接超时")
    
    whitelist_logger.database_connect_attempt(2, 3)
    whitelist_logger.database_connect_success(2)
    
    print("✅ 数据库连接日志功能测试完成")

def test_whitelist_operations():
    """测试白名单操作日志功能"""
    print("\n🧪 测试白名单操作日志功能...")
    
    # 测试白名单加载
    whitelist_logger.whitelist_load_start("database", "larkbusiness")
    test_items = ["测试用户1", "测试用户2", "测试用户3"]
    whitelist_logger.whitelist_load_success("database", "larkbusiness", len(test_items), test_items)
    
    # 测试白名单保存
    whitelist_logger.whitelist_save_start("database", "larkbusiness", len(test_items), test_items)
    whitelist_logger.whitelist_save_success("database", "larkbusiness", len(test_items))
    
    # 测试白名单同步
    whitelist_logger.whitelist_sync_start("database", "file", "larkbusiness")
    whitelist_logger.whitelist_sync_success("database", "file", "larkbusiness", len(test_items))
    
    print("✅ 白名单操作日志功能测试完成")

def test_web_request_logging():
    """测试Web请求日志功能"""
    print("\n🧪 测试Web请求日志功能...")
    
    # 测试Web请求
    whitelist_logger.web_request_start("/api/whitelist/lark", "POST", "lark")
    whitelist_logger.web_request_success("/api/whitelist/lark", "POST", "lark", {"count": 5})
    
    whitelist_logger.web_request_start("/api/whitelist/lark", "GET", "lark")
    whitelist_logger.web_request_failure("/api/whitelist/lark", "GET", "lark", "数据库连接失败")
    
    print("✅ Web请求日志功能测试完成")

def test_data_verification():
    """测试数据验证日志功能"""
    print("\n🧪 测试数据验证日志功能...")
    
    # 测试数据验证
    whitelist_logger.data_verification("save_count", 5, 5, True)  # 验证通过
    whitelist_logger.data_verification("load_count", 3, 2, False)  # 验证失败
    
    print("✅ 数据验证日志功能测试完成")

def test_complex_scenario():
    """测试复杂场景日志"""
    print("\n🧪 测试复杂场景日志...")
    
    # 模拟完整的白名单保存流程
    whitelist_logger.operation_start("web_save_whitelist", "lark")
    whitelist_logger.web_request_start("/api/whitelist/lark", "POST", "lark")
    
    # 模拟数据库连接
    whitelist_logger.database_connect_attempt(1, 1)
    whitelist_logger.database_connect_success(1)
    
    # 模拟保存操作
    test_items = ["用户A", "用户B", "用户C"]
    whitelist_logger.whitelist_save_start("database", "larkbusiness", len(test_items), test_items)
    whitelist_logger.whitelist_save_success("database", "larkbusiness", len(test_items))
    
    # 模拟验证
    whitelist_logger.data_verification("save_verification", len(test_items), len(test_items), True)
    
    # 模拟同步
    whitelist_logger.whitelist_sync_start("database", "file", "larkbusiness")
    whitelist_logger.whitelist_sync_success("database", "file", "larkbusiness", len(test_items))
    
    # 完成
    whitelist_logger.web_request_success("/api/whitelist/lark", "POST", "lark", {"count": len(test_items)})
    whitelist_logger.operation_success("web_save_whitelist", "lark", {"final_count": len(test_items)})
    
    print("✅ 复杂场景日志功能测试完成")

def show_log_file_info():
    """显示日志文件信息"""
    print(f"\n📄 日志文件信息:")
    print(f"📁 日志文件路径: {whitelist_logger.get_log_file_path()}")
    
    # 显示最近的几行日志
    recent_logs = whitelist_logger.get_recent_logs(10)
    if recent_logs:
        print(f"\n📋 最近 {len(recent_logs)} 行日志:")
        for i, line in enumerate(recent_logs, 1):
            print(f"  {i:2d}. {line.strip()}")
    else:
        print("📋 没有找到日志记录")

def main():
    """主测试函数"""
    print("🚀 开始测试白名单日志记录器")
    print("=" * 60)
    
    try:
        test_basic_logging()
        test_operation_logging()
        test_database_logging()
        test_whitelist_operations()
        test_web_request_logging()
        test_data_verification()
        test_complex_scenario()
        
        show_log_file_info()
        
        print("\n🎉 所有测试完成！")
        print("=" * 60)
        print("💡 提示:")
        print(f"   - 详细日志请查看: {whitelist_logger.get_log_file_path()}")
        print("   - 日志文件每天自动轮转")
        print("   - 所有白名单操作都会被记录")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 