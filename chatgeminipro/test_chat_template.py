#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试chat方法临时切换模板功能 - Gemini专用
"""

import asyncio
import sys
import pathlib
import traceback

# 添加项目根目录到Python路径
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from ..chat.postgreschattool import PostgresChatTool

def print_gemini_input(chat_tool, template_name, user_message, test_name):
    """打印Gemini API的真实输入内容"""
    print(f"\n=== {test_name} - 真实Input内容 ===")
    
    # 加载模板
    system_prompt = chat_tool._load_template(template_name or chat_tool.config.get('default_template', 'business'))
    print(f"使用模板: {template_name or '默认模板'}")
    print(f"模板内容: {system_prompt[:100]}..." if len(system_prompt) > 100 else f"模板内容: {system_prompt}")
    
    # 构建完整的input_text（模拟chat方法中的逻辑）
    input_text = system_prompt + "\n\n"
    
    # 添加历史消息（不包含系统消息）
    for msg in chat_tool.message_history:
        if msg.get('role') != 'system':
            role = "用户" if msg.get('role') == 'user' else "助手"
            input_text += f"{role}: {msg.get('content', '')}\n"
    
    # 添加当前用户消息
    input_text += f"用户: {user_message}\n助手: "
    
    print(f"真实的Gemini API Input:")
    print("-" * 30)
    print(input_text)
    print("-" * 30)
    print(f"Input总长度: {len(input_text)}字符")

async def test_chat_template_switching():
    """测试chat方法是否能临时切换模板"""
    chat_tool = PostgresChatTool()
    
    try:
        print("===初始化聊天工具===")
        initialized = await chat_tool.initialize()
        if not initialized:
            print("初始化失败")
            return

        # 显示API配置信息
        print(f"当前API类型: {chat_tool.config.get('api_type', 'gemini')}")
        print(f"当前模型: {chat_tool.config.get('model', 'gemini-2.0-flash')}")
        print(f"API密钥: {'已设置' if chat_tool.config.get('api_key') else '未设置'}")
        
        if not chat_tool.config.get('api_key'):
            print("错误: API密钥未设置！")
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
        
        # 测试问题
        test_question = "请做一个简短的自我介绍"
        
        # 使用默认模板进行对话
        print("\n===使用默认模板进行对话===")
        print_gemini_input(chat_tool, None, test_question, "默认模板测试")
        try:
            default_response = await asyncio.wait_for(
                chat_tool.chat(test_question),
                timeout=30.0
            )
            print(f"默认模板回复: {default_response}")
            print(f"回复长度: {len(default_response)}字符")
        except asyncio.TimeoutError:
            print("默认模板回复超时")
            return
        except Exception as e:
            print(f"默认模板回复出错: {e}")
            return
        
        # 使用简短模板进行对话
        print("\n===使用简短模板进行对话===")
        print_gemini_input(chat_tool, short_template, test_question, "简短模板测试")
        try:
            short_response = await asyncio.wait_for(
                chat_tool.chat(test_question, template_name=short_template),
                timeout=30.0
            )
            print(f"简短模板回复: {short_response}")
            print(f"回复长度: {len(short_response)}字符")
        except asyncio.TimeoutError:
            print("简短模板回复超时")
            return
        except Exception as e:
            print(f"简短模板回复出错: {e}")
            return
        
        # 使用冗长模板进行对话
        print("\n===使用冗长模板进行对话===")
        print_gemini_input(chat_tool, long_template, test_question, "冗长模板测试")
        try:
            long_response = await asyncio.wait_for(
                chat_tool.chat(test_question, template_name=long_template),
                timeout=30.0
            )
            print(f"冗长模板回复: {long_response}")
            print(f"回复长度: {len(long_response)}字符")
        except asyncio.TimeoutError:
            print("冗长模板回复超时")
            return
        except Exception as e:
            print(f"冗长模板回复出错: {e}")
            return
        
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
            print("注意: 模板效果可能因AI模型的行为而有所不同")
        
    except Exception as e:
        print(f"\n测试过程中发生异常: {type(e).__name__}: {str(e)}")
        print("详细错误信息:")
        traceback.print_exc()
        
    finally:
        # 关闭连接
        await chat_tool.close()
        print("\n测试完成，连接已关闭")

if __name__ == "__main__":
    print("Gemini API 模板切换功能测试")
    print(f"Python版本: {sys.version}")
    print(f"项目根目录: {project_root}")
    print("-" * 50)
    
    asyncio.run(test_chat_template_switching()) 