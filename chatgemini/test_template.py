#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模板加载测试脚本 - Gemini专用
"""

import asyncio
import pathlib
import sys
import os
import traceback

# 添加项目根目录到Python路径
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from typing import Dict, Any, Optional, List, Tuple, Union

# 现在可以正确导入模块
from ..chatgemini.postgreschattool import PostgresChatTool

async def reply_with_template(user_input: str) -> str:
    """
    使用星职盟评论回复模板回复用户输入
    
    Args:
        user_input: 用户输入的消息
        
    Returns:
        AI助手的回复
    """
    # 初始化聊天工具
    chat_tool = PostgresChatTool()
    
    try:
        # 初始化数据库连接
        print("开始初始化聊天工具...")
        await chat_tool.initialize()
        
        # 检查API配置
        print(f"API配置检查:")
        print(f"  - API类型: {chat_tool.config.get('api_type', 'gemini')}")
        print(f"  - 模型: {chat_tool.config.get('model', 'gemini-2.0-flash')}")
        print(f"  - API密钥: {'已设置' if chat_tool.config.get('api_key') else '未设置'}")
        
        # 检查API密钥
        if not chat_tool.config.get('api_key'):
            print("错误: API密钥未设置！请在 config/default.json 中设置 api_key")
            return "API密钥未设置"
        
        # 使用星职盟评论回复模板
        template_name = "星职盟评论回复"
        
        # 创建会话
        session_name = "模板测试会话"
        print(f"创建/设置会话: {session_name}")
        await chat_tool.set_session(session_name, template_name=template_name)
        
        # 构建真实的input内容用于调试
        print("\n=== 构建真实Input内容 ===")
        system_prompt = chat_tool._load_template(template_name)
        print(f"使用模板: {template_name}")
        print(f"模板内容: {system_prompt[:200]}..." if len(system_prompt) > 200 else f"模板内容: {system_prompt}")
        
        # 构建完整的input_text（模拟chat方法中的逻辑）
        input_text = system_prompt + "\n\n"
        
        # 添加当前用户消息
        input_text += f"用户: {user_input}\n助手: "
        
        print(f"\n真实的Gemini API Input:")
        print("-" * 50)
        print(input_text)
        print("-" * 50)
        print(f"Input总长度: {len(input_text)}字符")
        
        # 发送消息并获取回复
        print(f"\n发送消息: {user_input}")
        print("等待AI回复...")
        
        # 添加超时设置
        try:
            response = await asyncio.wait_for(
                chat_tool.chat(user_input, template_name=template_name),
                timeout=30.0  # 30秒超时
            )
            return response
        except asyncio.TimeoutError:
            print("错误: 聊天请求超时(30秒)")
            return "聊天请求超时"
        
    except Exception as e:
        print(f"发生异常: {type(e).__name__}: {str(e)}")
        print("详细错误信息:")
        traceback.print_exc()
        return f"发生错误: {str(e)}"
        
    finally:
        # 关闭连接
        await chat_tool.close()

async def test_template():
    """测试模板加载功能"""
    user_message = "你好！"
    print(f"发送消息: {user_message}")
    
    response = await reply_with_template(user_message)
    print(f"收到回复: {response}")

if __name__ == "__main__":
    # 设置事件循环
    print("Gemini API 模板测试")
    print("Python版本:", sys.version)
    print("当前目录:", os.getcwd())
    print("项目根目录:", project_root)
    print("-" * 50)
    
    asyncio.run(test_template())