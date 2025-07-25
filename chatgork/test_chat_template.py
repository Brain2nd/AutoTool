#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试chat方法临时切换模板功能
"""

import asyncio
import sys
import pathlib

# 添加项目根目录到Python路径
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from ..chatgork.postgreschattool import PostgresChatTool

async def test_chat_template_switching():
    """测试chat方法是否能临时切换模板"""
    chat_tool = PostgresChatTool()
    
    try:
        print("===初始化聊天工具===")
        initialized = await chat_tool.initialize()
        if not initialized:
            print("初始化失败")
            return

        # 创建两个不同的测试模板
        print("\n===创建两个不同的测试模板===")
        # 创建简短模板
        short_template = "short_test"
        short_content = "你是一个简短回复助手。所有回复必须少于20字。"
        chat_tool.save_template(short_template, short_content)
        print(f"创建简短模板: {short_template}")
        
        # 创建冗长模板
        long_template = "long_test"
        long_content = "你是一个详细解释助手。所有回复必须超过100字，并包含多个例子和详细说明。"
        chat_tool.save_template(long_template, long_content)
        print(f"创建冗长模板: {long_template}")

        # 列出所有模板
        templates = chat_tool.list_templates()
        
        # 设置会话，使用config的默认模板(business)
        print("\n===设置会话(使用默认模板)===")
        session_name = "模板切换测试"
        session_id, cache_id = await chat_tool.set_session(session_name)
        print(f"会话ID: {session_id}, 缓存ID: {cache_id}")
        
        # 使用默认模板进行对话
        print("\n===使用默认模板进行对话===")
        default_response = await chat_tool.chat("请做一个简短的自我介绍")
        print(f"默认模板回复: {default_response}")
        print(f"回复长度: {len(default_response)}字符")
        
        # 使用简短模板进行对话
        print("\n===使用简短模板进行对话===")
        short_response = await chat_tool.chat("请做一个简短的自我介绍", template_name=short_template)
        print(f"简短模板回复: {short_response}")
        print(f"回复长度: {len(short_response)}字符")
        
        # 使用冗长模板进行对话
        print("\n===使用冗长模板进行对话===")
        long_response = await chat_tool.chat("请做一个简短的自我介绍", template_name=long_template)
        print(f"冗长模板回复: {long_response}")
        print(f"回复长度: {len(long_response)}字符")
        
        # 验证是否切换了模板
        print("\n===验证结果===")
        is_short_shorter = len(short_response) < len(default_response)
        is_long_longer = len(long_response) > len(default_response)
        
        if is_short_shorter:
            print("✓ 简短模板确实生成了更短的回复")
        else:
            print("× 简短模板没有生成更短的回复")
            
        if is_long_longer:
            print("✓ 冗长模板确实生成了更长的回复")
        else:
            print("× 冗长模板没有生成更长的回复")
            
        print(f"\n简短/默认/冗长回复长度比较: {len(short_response)} / {len(default_response)} / {len(long_response)}")
        
        # 最终结论
        if is_short_shorter and is_long_longer:
            print("\n结论: chat方法成功实现了临时切换模板功能 ✓")
        else:
            print("\n结论: chat方法未能成功实现临时切换模板功能 ×")
        
    finally:
        # 关闭连接
        await chat_tool.close()
        print("\n测试完成，连接已关闭")

if __name__ == "__main__":
    asyncio.run(test_chat_template_switching()) 