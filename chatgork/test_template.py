#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模板加载测试脚本
"""

import asyncio
import pathlib
import sys
import os
import traceback
import httpx

# 添加项目根目录到Python路径
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from typing import Dict, Any, Optional, List, Tuple, Union

# 现在可以正确导入模块
from ..chat.postgreschattool import PostgresChatTool

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
        print(f"  - API类型: {chat_tool.config.get('api_type', 'openai')}")
        print(f"  - 基础URL: {chat_tool.config.get('base_url', 'https://api.openai.com/v1')}")
        print(f"  - 模型: {chat_tool.config.get('model', 'gpt-3.5-turbo')}")
        print(f"  - API密钥: {'已设置' if chat_tool.config.get('api_key') else '未设置'}")
        print(f"  - 温度: {chat_tool.config.get('temperature', 0.7)}")
        print(f"  - 最大令牌数: {chat_tool.config.get('max_tokens', 1000)}")
        
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
        
        # 测试网络连接
        print("测试API连接...")
        try:
            # 使用httpx测试连接
            async with httpx.AsyncClient(timeout=10.0) as client:
                base_url = chat_tool.config.get('base_url', 'https://api.openai.com/v1')
                test_url = f"{base_url}/models"
                headers = {"Authorization": f"Bearer {chat_tool.config.get('api_key')}"}
                
                print(f"测试URL: {test_url}")
                response = await client.get(test_url, headers=headers)
                print(f"API连接测试结果: {response.status_code}")
                if response.status_code != 200:
                    print(f"API响应内容: {response.text[:500]}")
        except Exception as e:
            print(f"API连接测试失败: {type(e).__name__}: {str(e)}")
        
        # 发送消息并获取回复
        print(f"发送消息: {user_input}")
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
    print(f"收到回复: {response[:100]}...")

if __name__ == "__main__":
    # 设置事件循环
    print("Python版本:", sys.version)
    print("当前目录:", os.getcwd())
    print("项目根目录:", project_root)
    print("-" * 50)
    
    asyncio.run(test_template())