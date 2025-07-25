#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试编译后的whl包功能
"""

import sys
import traceback

def test_imports():
    """测试所有模块的导入"""
    test_results = []
    
    # 测试浏览器工具
    try:
        from autotool.browser.browsertool import BrowserTool
        test_results.append(("✅ BrowserTool", "成功导入"))
    except Exception as e:
        test_results.append(("❌ BrowserTool", f"导入失败: {str(e)}"))
    
    # 测试数据库工具
    try:
        from autotool.db.postgrestool import PostgresTool
        test_results.append(("✅ PostgresTool", "成功导入"))
    except Exception as e:
        test_results.append(("❌ PostgresTool", f"导入失败: {str(e)}"))
    
    # 测试聊天工具
    try:
        from autotool.chat.postgreschattool import PostgresChatTool
        test_results.append(("✅ PostgresChatTool", "成功导入"))
    except Exception as e:
        test_results.append(("❌ PostgresChatTool", f"导入失败: {str(e)}"))
    
    # 测试缓存工具
    try:
        from autotool.cache.postgrescachetool import PostgresCacheTool
        test_results.append(("✅ PostgresCacheTool", "成功导入"))
    except Exception as e:
        test_results.append(("❌ PostgresCacheTool", f"导入失败: {str(e)}"))
    
    # 测试微信工具
    try:
        from autotool.wx.AsyncWxTool import AsyncWxTool
        test_results.append(("✅ AsyncWxTool", "成功导入"))
    except Exception as e:
        test_results.append(("❌ AsyncWxTool", f"导入失败: {str(e)}"))
    
    # 测试RAG工具
    try:
        from autotool.rag.ragtool import RAGTool
        test_results.append(("✅ RAGTool", "成功导入"))
    except Exception as e:
        test_results.append(("❌ RAGTool", f"导入失败: {str(e)}"))
    
    return test_results

def test_basic_functionality():
    """测试基本功能"""
    test_results = []
    
    # 测试浏览器工具基本功能
    try:
        from autotool.browser.browsertool import BrowserTool
        browser_tool = BrowserTool()
        test_results.append(("✅ BrowserTool 实例化", "成功创建实例"))
    except Exception as e:
        test_results.append(("❌ BrowserTool 实例化", f"失败: {str(e)}"))
    
    # 测试数据库工具基本功能
    try:
        from autotool.db.postgrestool import PostgresTool
        db_tool = PostgresTool()
        test_results.append(("✅ PostgresTool 实例化", "成功创建实例"))
    except Exception as e:
        test_results.append(("❌ PostgresTool 实例化", f"失败: {str(e)}"))
    
    # 测试聊天工具基本功能
    try:
        from autotool.chat.postgreschattool import PostgresChatTool
        chat_tool = PostgresChatTool()
        test_results.append(("✅ PostgresChatTool 实例化", "成功创建实例"))
    except Exception as e:
        test_results.append(("❌ PostgresChatTool 实例化", f"失败: {str(e)}"))
    
    return test_results

def test_config_files():
    """测试配置文件是否正确包含"""
    test_results = []
    
    try:
        from autotool.chat.postgreschattool import PostgresChatTool
        chat_tool = PostgresChatTool()
        # 尝试加载配置
        config = chat_tool._load_config("default")
        test_results.append(("✅ 配置文件加载", "成功加载默认配置"))
    except Exception as e:
        test_results.append(("❌ 配置文件加载", f"失败: {str(e)}"))
    
    return test_results

def main():
    """主测试函数"""
    print("🚀 开始测试AutoOOIN工具包...")
    print("=" * 60)
    
    # 测试导入
    print("\n📦 测试模块导入...")
    import_results = test_imports()
    for status, message in import_results:
        print(f"{status}: {message}")
    
    # 测试基本功能
    print("\n⚙️ 测试基本功能...")
    func_results = test_basic_functionality()
    for status, message in func_results:
        print(f"{status}: {message}")
    
    # 测试配置文件
    print("\n📋 测试配置文件...")
    config_results = test_config_files()
    for status, message in config_results:
        print(f"{status}: {message}")
    
    # 统计结果
    all_results = import_results + func_results + config_results
    success_count = sum(1 for status, _ in all_results if status.startswith("✅"))
    total_count = len(all_results)
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {success_count}/{total_count} 通过")
    
    if success_count == total_count:
        print("🎉 所有测试通过！whl包构建成功！")
        return 0
    else:
        print("⚠️ 存在测试失败，请检查构建过程")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 