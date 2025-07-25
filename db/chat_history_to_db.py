#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
聊天历史导入数据库工具
演示如何使用SCAdatabaseTool将聊天历史保存到数据库
"""

import os
import sys
import json
import asyncio
import pathlib
from datetime import datetime

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入数据库工具
from ..db.SCAdatabaseTool import SCAdatabaseTool
# 导入聊天历史收集功能
from task.sca.function.chat_history_collector import extract_chat_history


async def import_chat_history_from_file(file_path):
    """
    从JSON文件导入聊天历史到数据库
    
    Args:
        file_path: JSON文件路径
    
    Returns:
        是否成功导入
    """
    try:
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
        
        # 初始化数据库工具
        db = SCAdatabaseTool()
        await db.connect()
        
        # 提取基本信息
        chat_name = chat_data.get('chat_partner', '未知聊天')
        app_type = chat_data.get('chat_app_type', 'xiaohongshu')  # 默认小红书
        is_group = chat_data.get('is_group', False)
        messages = chat_data.get('messages', [])
        stats = chat_data.get('stats', {})
        
        if not messages:
            print("JSON文件中没有消息可导入")
            return False
        
        # 收集时间
        collection_time = datetime.now()
        if 'collection_time' in chat_data:
            try:
                # 尝试解析已有的收集时间
                time_str = chat_data['collection_time']
                collection_time = datetime.strptime(time_str, "%Y%m%d_%H%M%S")
            except:
                pass
        
        # 获取或创建聊天ID
        chat_id = await db.get_chat_id(chat_name, app_type, is_group)
        
        # 添加聊天历史记录
        history_id = await db.add_chat_history(
            chat_id=chat_id,
            collection_time=collection_time,
            is_group=is_group,
            online_count=chat_data.get('online_count'),
            total_members=chat_data.get('total_members'),
            stats=stats
        )
        
        # 批量添加消息
        message_count = await db.add_messages(history_id, messages)
        
        # 更新统计信息
        if stats:
            await db.update_chat_history_stats(history_id, stats, message_count)
        
        print(f"成功从文件导入 {message_count} 条消息到数据库")
        return True
    
    except Exception as e:
        print(f"导入聊天历史失败: {e}")
        return False
    
    finally:
        # 关闭数据库连接
        if 'db' in locals():
            await db.close()


async def collect_and_save_chat_history():
    """直接收集并保存聊天历史到数据库"""
    
    # 收集聊天历史
    print("开始收集聊天历史...")
    chat_result = extract_chat_history()
    
    if not chat_result.get('success', False):
        print(f"聊天历史收集失败: {chat_result.get('message', '未知错误')}")
        return False
    
    # 初始化数据库工具
    db = SCAdatabaseTool()
    
    try:
        # 连接数据库
        await db.connect()
        
        # 获取基本信息
        chat_name = chat_result.get('chat_partner', '未知聊天')
        app_type = chat_result.get('chat_app_type', 'xiaohongshu')  # 默认小红书
        is_group = chat_result.get('is_group', False)
        messages = chat_result.get('chat_messages', [])
        stats = chat_result.get('stats', {})
        
        if not messages:
            print("没有消息可保存")
            return False
        
        print(f"收集到 {len(messages)} 条消息，准备保存到数据库")
        print(f"聊天对象: {chat_name}")
        print(f"应用类型: {app_type}")
        
        # 获取或创建聊天ID
        chat_id = await db.get_chat_id(chat_name, app_type, is_group)
        
        # 收集时间
        collection_time = datetime.now()
        
        # 添加聊天历史记录
        history_id = await db.add_chat_history(
            chat_id=chat_id,
            collection_time=collection_time,
            is_group=is_group,
            online_count=chat_result.get('online_count'),
            total_members=chat_result.get('total_members'),
            stats=stats
        )
        
        # 批量添加消息
        message_count = await db.add_messages(history_id, messages)
        
        # 更新统计信息
        if stats:
            await db.update_chat_history_stats(history_id, stats, message_count)
        
        print(f"成功保存 {message_count} 条消息到数据库")
        
        # 显示聊天统计信息
        if stats:
            print("\n===== 统计信息 =====")
            print(f"总消息数: {stats.get('total_messages', 0)}")
            print(f"自己发送: {stats.get('self_messages', 0)} 条")
            print(f"对方发送: {stats.get('other_messages', 0)} 条")
            
            msg_types = stats.get('message_types', {})
            if msg_types:
                print("\n消息类型分布:")
                for msg_type, count in msg_types.items():
                    print(f"  {msg_type}: {count} 条")
        
        return True
    
    except Exception as e:
        print(f"保存聊天历史到数据库失败: {e}")
        return False
    
    finally:
        # 关闭数据库连接
        await db.close()


async def list_all_chats():
    """列出数据库中的所有聊天"""
    db = SCAdatabaseTool()
    
    try:
        await db.connect()
        
        # 获取所有聊天
        chats = await db.get_chats()
        
        if not chats:
            print("数据库中没有聊天记录")
            return
        
        print(f"数据库中共有 {len(chats)} 个聊天记录:")
        for i, chat in enumerate(chats, 1):
            print(f"{i}. {chat['name']} (类型: {chat['app_type']})")
            print(f"   - ID: {chat['id']}")
            print(f"   - 群聊: {'是' if chat['is_group'] else '否'}")
            print(f"   - 历史记录: {chat['history_count']} 次")
            print(f"   - 消息总数: {chat['total_message_count'] or 0} 条")
            print(f"   - 最后更新: {chat['last_updated']}")
            print()
        
    except Exception as e:
        print(f"列出聊天记录失败: {e}")
    
    finally:
        await db.close()


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='聊天历史数据库工具')
    
    # 添加子命令
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 导入文件子命令
    import_parser = subparsers.add_parser('import', help='从JSON文件导入聊天历史')
    import_parser.add_argument('file', help='JSON文件路径')
    
    # 收集聊天历史子命令
    collect_parser = subparsers.add_parser('collect', help='收集并保存当前聊天历史')
    
    # 列出所有聊天子命令
    list_parser = subparsers.add_parser('list', help='列出数据库中所有聊天')
    
    # 解析参数
    args = parser.parse_args()
    
    # 根据命令执行对应操作
    if args.command == 'import':
        asyncio.run(import_chat_history_from_file(args.file))
    elif args.command == 'collect':
        asyncio.run(collect_and_save_chat_history())
    elif args.command == 'list':
        asyncio.run(list_all_chats())
    else:
        parser.print_help() 