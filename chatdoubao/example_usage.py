#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
豆包API使用示例

展示如何使用豆包（火山方舟）API进行聊天
"""

import asyncio
import os
from openai import AsyncOpenAI


async def simple_doubao_example():
    """简单豆包API调用示例"""
    print("=" * 50)
    print("豆包API简单调用示例")
    print("=" * 50)
    
    # 1. 检查环境变量
    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        print("❌ 请设置环境变量 ARK_API_KEY")
        print("   示例: export ARK_API_KEY='your-api-key-here'")
        return
    
    # 2. 获取模型ID
    model_id = input("请输入豆包模型ID (如: ep-20241001234567-abcde): ").strip()
    if not model_id:
        print("❌ 模型ID不能为空")
        return
    
    try:
        # 3. 创建客户端
        print("\\n正在初始化豆包客户端...")
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3"
        )
        
        # 4. 构建消息
        messages = [
            {"role": "system", "content": "你是一个智能助手，请用中文回答问题。"},
            {"role": "user", "content": "你好，请简单介绍一下自己"}
        ]
        
        print(f"正在调用豆包API...")
        print(f"  - 模型: {model_id}")
        print(f"  - 消息数量: {len(messages)}")
        
        # 5. 调用API
        response = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        # 6. 显示结果
        ai_response = response.choices[0].message.content
        print("\\n" + "="*50)
        print("豆包回复:")
        print("="*50)
        print(ai_response)
        print("="*50)
        print("✅ API调用成功！")
        
    except Exception as e:
        print(f"❌ API调用失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("豆包API使用示例")
    print("\\n此示例展示如何直接调用豆包API")
    print("基于您提供的配置模板创建")
    
    asyncio.run(simple_doubao_example())