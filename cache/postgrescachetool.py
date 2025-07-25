#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
聊天缓存管理工具 - PostgreSQL异步版本

提供聊天记录缓存的创建、查询和管理功能
"""

import os
import json
import asyncio
import asyncpg
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class PostgresCacheTool:
    """聊天缓存数据库工具类，基于PostgreSQL的异步实现，提供聊天缓存的统一管理接口"""
    
    def __init__(self, 
                user: str = 'YOUR_DATABASE_USER_HERE',
                password: str = 'YOUR_DATABASE_PASSWORD_HERE',
                database: str = 'postgres',
                host: str = 'YOUR_DATABASE_HOST_HERE',
                port: int = 5432  # Change to YOUR_DATABASE_PORT_HERE):
        """
        初始化缓存工具
        
        Args:
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名称
            host: 数据库主机
            port: 数据库端口
        """
        self.conn_params = {
            'user': user,
            'password': password,
            'database': database,
            'host': host,
            'port': port
        }
        self.pool = None
    
    async def connect(self):
        """连接到数据库"""
        try:
            self.pool = await asyncpg.create_pool(**self.conn_params)
            # 如果是新数据库，初始化表结构
            await self._check_and_init_db()
            return True
        except Exception as e:
            print(f"连接缓存数据库失败: {e}")
            return False
    
    async def _check_and_init_db(self):
        """检查并初始化数据库表结构"""
        async with self.pool.acquire() as conn:
            try:
                # 检查chat_caches表是否存在
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = 'chat_caches'
                    )
                """)
                
                if not exists:
                    # 数据库表不存在，初始化数据库
                    await self._init_db(conn)
                else:
                    # 表存在，检查是否需要升级表结构
                    await self._check_and_upgrade_structure(conn)
            except Exception as e:
                print(f"检查数据库结构时出错: {e}")
                # 出错时尝试创建表
                await self._init_db(conn)
    
    async def _init_db(self, conn):
        """初始化数据库表结构"""
        try:
            # 使用事务确保原子操作
            async with conn.transaction():
                # 聊天缓存表
                await conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_caches (
                    id SERIAL PRIMARY KEY,
                    linked_session_id INTEGER,
                    model TEXT NOT NULL,
                    api_type TEXT NOT NULL,
                    temperature REAL NOT NULL,
                    system_prompt TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    token_count INTEGER DEFAULT 0
                )''')
                
                # 聊天消息引用表 - 修改为引用微信消息而非存储完整内容
                await conn.execute('''
                CREATE TABLE IF NOT EXISTS cache_messages (
                    id SERIAL PRIMARY KEY,
                    cache_id INTEGER NOT NULL REFERENCES chat_caches(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    message_id INTEGER,           -- 微信数据库中的消息ID，如果是从微信同步的消息
                    content TEXT,                 -- 如果是系统消息等非微信消息，才使用此字段
                    raw_response TEXT,            -- 存储原始的模型响应（包含JSON）
                    parsed_response TEXT,         -- 存储解析后的响应文本
                    status_code TEXT,             -- 存储状态码
                    sequence_number INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_wx_message BOOLEAN DEFAULT FALSE  -- 标记是否为微信消息
                )''')
                
                # 创建索引
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_linked_session ON chat_caches(linked_session_id)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_cache_messages_cache ON cache_messages(cache_id)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_cache_messages_sequence ON cache_messages(sequence_number)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_cache_messages_is_wx ON cache_messages(is_wx_message)')
                
                print("缓存数据库表结构初始化成功")
        except Exception as e:
            print(f"初始化数据库表结构失败: {e}")
            raise
    
    async def _check_and_upgrade_structure(self, conn):
        """检查并升级数据库结构"""
        try:
            # 获取当前表结构
            columns = await conn.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'cache_messages'
            """)
            
            current_columns = [col['column_name'] for col in columns]
            
            # 检查是否需要添加新列
            needs_upgrade = False
            for column in ['raw_response', 'parsed_response', 'status_code']:
                if column not in current_columns:
                    needs_upgrade = True
                    break
            
            if needs_upgrade:
                print(f"缓存数据库需要升级，正在添加新字段...")
                
                # 添加缺失的列
                async with conn.transaction():
                    for column in ['raw_response', 'parsed_response', 'status_code']:
                        if column not in current_columns:
                            try:
                                await conn.execute(f"ALTER TABLE cache_messages ADD COLUMN {column} TEXT")
                                print(f"已添加列: {column}")
                            except Exception:
                                # 如果列已存在，继续
                                pass
                    
                    # 更新现有记录
                    print("更新现有记录...")
                    await conn.execute("""
                    UPDATE cache_messages
                    SET raw_response = content, parsed_response = content
                    WHERE role = 'assistant' AND raw_response IS NULL
                    """)
                    
                print("缓存数据库升级完成")
        except Exception as e:
            print(f"升级数据库结构时出错: {e}")
            # 继续使用现有结构，错误不终止程序
    
    async def save_chat_cache(self, linked_session_id: Optional[int], model: str, api_type: str,
                           temperature: float, system_prompt: str, messages: List[Dict[str, str]],
                           token_count: int = 0) -> int:
        """
        保存聊天缓存
        
        Args:
            linked_session_id: 关联的微信会话ID，可选
            model: 使用的模型名称
            api_type: API类型（如openai、xai等）
            temperature: 模型温度参数
            system_prompt: 模板名称（而非完整内容）
            messages: 消息列表，可以包含raw_response, parsed_response, status_code
            token_count: 总token数，默认为0
            
        Returns:
            新增的cache_id
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # 1. 插入聊天缓存
                now = datetime.now()  # 使用datetime对象而非字符串
                cache_id = await conn.fetchval('''
                INSERT INTO chat_caches 
                (linked_session_id, model, api_type, temperature, system_prompt, created_at, last_used, token_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                ''', 
                linked_session_id, model, api_type, temperature, system_prompt, 
                now, now, token_count)
                
                # 2. 插入消息 - 即使消息列表为空，也确保消息表被创建
                if messages:
                    for i, message in enumerate(messages):
                        role = message.get('role', 'unknown')
                        content = message.get('content', '')
                        raw_response = message.get('raw_response')
                        parsed_response = message.get('parsed_response')
                        status_code = message.get('status_code')
                        
                        await conn.execute('''
                        INSERT INTO cache_messages
                        (cache_id, role, message_id, content, sequence_number, raw_response, parsed_response, status_code)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ''', 
                        cache_id, role, message.get('id'), content, i,
                        raw_response, parsed_response, status_code)
                else:
                    # 即使没有消息，也创建一个空记录以确保表存在
                    await conn.execute('''
                    INSERT INTO cache_messages
                    (cache_id, role, message_id, content, sequence_number, raw_response, parsed_response, status_code)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ''', 
                    cache_id, "system", None, "", 0, None, None, None)
                
                return cache_id
    
    async def update_chat_cache(self, cache_id: int, new_messages: List[Dict[str, str]],
                             token_count: Optional[int] = None) -> bool:
        """
        更新现有聊天缓存
        
        Args:
            cache_id: 聊天缓存ID
            new_messages: 新的消息列表（将替换旧消息）
            token_count: 新的token计数，可选
            
        Returns:
            操作是否成功
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # 1. 更新缓存最后使用时间和token计数
                    now = datetime.now()  # 使用datetime对象而非字符串
                    
                    if token_count is not None:
                        await conn.execute('''
                        UPDATE chat_caches
                        SET last_used = $1, token_count = $2
                        WHERE id = $3
                        ''', now, token_count, cache_id)
                    else:
                        await conn.execute('''
                        UPDATE chat_caches
                        SET last_used = $1
                        WHERE id = $2
                        ''', now, cache_id)
                    
                    # 2. 删除旧消息
                    await conn.execute('DELETE FROM cache_messages WHERE cache_id = $1', cache_id)
                    
                    # 3. 插入新消息
                    for i, message in enumerate(new_messages):
                        role = message.get('role', 'unknown')
                        content = message.get('content', '')
                        raw_response = message.get('raw_response')
                        parsed_response = message.get('parsed_response')
                        status_code = message.get('status_code')
                        
                        await conn.execute('''
                        INSERT INTO cache_messages
                        (cache_id, role, message_id, content, sequence_number, raw_response, parsed_response, status_code)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ''', 
                        cache_id, role, message.get('id'), content, i,
                        raw_response, parsed_response, status_code)
                
                return True
        except Exception as e:
            print(f"更新聊天缓存时出错: {e}")
            return False
    
    async def get_chat_cache(self, cache_id: int, db_tool = None) -> Optional[Dict[str, Any]]:
        """
        获取聊天缓存和消息
        
        Args:
            cache_id: 聊天缓存ID
            db_tool: 可选的DBTool实例，用于获取微信消息
            
        Returns:
            包含缓存信息和消息的字典
        """
        async with self.pool.acquire() as conn:
            # 1. 获取缓存信息
            cache_row = await conn.fetchrow('''
            SELECT id, linked_session_id, model, api_type, temperature, system_prompt, 
                   created_at, last_used, token_count
            FROM chat_caches
            WHERE id = $1
            ''', cache_id)
            
            if not cache_row:
                return None
                
            # 构建缓存信息
            cache_info = dict(cache_row)
            cache_info['messages'] = []
            
            # 2. 获取消息
            message_rows = await conn.fetch('''
            SELECT id, role, message_id, content, sequence_number, created_at, is_wx_message, 
                   raw_response, parsed_response, status_code
            FROM cache_messages
            WHERE cache_id = $1
            ORDER BY sequence_number
            ''', cache_id)
            
            # 创建微信消息ID到消息的映射，用于快速查找
            wx_messages = {}
            linked_session_id = cache_info['linked_session_id']
            
            if db_tool and linked_session_id:
                # 检查db_tool是否是异步工具
                if hasattr(db_tool, 'get_messages_by_session_id'):
                    # 同步工具
                    session_messages = db_tool.get_messages_by_session_id(linked_session_id)
                    wx_messages = {msg['id']: msg for msg in session_messages if 'id' in msg}
                elif hasattr(db_tool, 'get_messages'):
                    # 异步工具，但需要我们手动获取所有消息
                    messages = await db_tool.get_messages(linked_session_id, limit=1000)
                    wx_messages = {msg['id']: msg for msg in messages if 'id' in msg}
            
            for msg_row in message_rows:
                message = dict(msg_row)
                message['is_wx_message'] = bool(message['is_wx_message'])
                
                # 如果是微信消息并且提供了DBTool，尝试获取微信消息内容
                if message['message_id'] and db_tool and message['is_wx_message']:
                    if message['message_id'] in wx_messages:
                        wx_msg = wx_messages[message['message_id']]
                        # 使用微信消息的内容替换缓存中的内容
                        message['content'] = wx_msg.get('content', message['content'])
                        message['wx_sender'] = wx_msg.get('sender', 'unknown')
                        message['wx_created_at'] = wx_msg.get('created_at', str(message['created_at']))
                
                cache_info['messages'].append(message)
                
            return cache_info
    
    async def get_chat_messages(self, cache_id: int) -> List[Dict[str, str]]:
        """
        获取聊天消息列表，格式适合OpenAI API调用
        
        Args:
            cache_id: 聊天缓存ID
            
        Returns:
            消息列表，每条消息包含role和content字段
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
            SELECT role, message_id, content, raw_response, parsed_response, status_code
            FROM cache_messages
            WHERE cache_id = $1
            ORDER BY sequence_number
            ''', cache_id)
            
            messages = []
            for row in rows:
                message = {
                    'role': row['role'],
                    'message_id': row['message_id'],
                    'content': row['content']
                }
                
                # 添加可选字段（如果存在）
                if row['raw_response']:
                    message['raw_response'] = row['raw_response']
                if row['parsed_response']:
                    message['parsed_response'] = row['parsed_response']
                if row['status_code']:
                    message['status_code'] = row['status_code']
                    
                messages.append(message)
                
            return messages
    
    async def list_chat_caches(self, linked_session_id: Optional[int] = None, 
                            limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        列出聊天缓存
        
        Args:
            linked_session_id: 微信会话ID，可选，用于过滤特定会话关联的缓存
            limit: 返回结果数量限制
            offset: 分页偏移量
            
        Returns:
            缓存信息列表
        """
        async with self.pool.acquire() as conn:
            if linked_session_id is not None:
                rows = await conn.fetch('''
                SELECT c.id, c.linked_session_id, c.model, c.api_type, c.system_prompt,
                       c.created_at, c.last_used, c.token_count,
                       (SELECT COUNT(*) FROM cache_messages WHERE cache_id = c.id) as message_count
                FROM chat_caches c
                WHERE c.linked_session_id = $1
                ORDER BY c.last_used DESC
                LIMIT $2 OFFSET $3
                ''', linked_session_id, limit, offset)
            else:
                rows = await conn.fetch('''
                SELECT c.id, c.linked_session_id, c.model, c.api_type, c.system_prompt,
                       c.created_at, c.last_used, c.token_count,
                       (SELECT COUNT(*) FROM cache_messages WHERE cache_id = c.id) as message_count
                FROM chat_caches c
                ORDER BY c.last_used DESC
                LIMIT $1 OFFSET $2
                ''', limit, offset)
            
            return [dict(row) for row in rows]
    
    async def delete_chat_cache(self, cache_id: int) -> bool:
        """
        删除聊天缓存及其消息
        
        Args:
            cache_id: 聊天缓存ID
            
        Returns:
            操作是否成功
        """
        try:
            async with self.pool.acquire() as conn:
                # 由于设置了外键约束和CASCADE，只需删除缓存，消息会自动删除
                result = await conn.execute('''
                DELETE FROM chat_caches
                WHERE id = $1
                ''', cache_id)
                
                # 检查是否有记录被删除
                return 'DELETE' in result
        except Exception as e:
            print(f"删除聊天缓存时出错: {e}")
            return False
    
    async def get_client_config(self, cache_id: int) -> Dict[str, Any]:
        """
        获取重建客户端所需的配置
        
        Args:
            cache_id: 聊天缓存ID
            
        Returns:
            包含API配置的字典
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
            SELECT api_type, model, temperature, system_prompt
            FROM chat_caches
            WHERE id = $1
            ''', cache_id)
            
            if not row:
                return {}
                
            return {
                'api_type': row['api_type'],
                'model': row['model'],
                'temperature': row['temperature'],
                'template': row['system_prompt']  # 返回template名称，与ChatTool兼容
            }

    async def clear_all_cache(self) -> bool:
        """
        清空所有缓存数据
        
        Returns:
            操作是否成功
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # 由于有外键关联，先清空消息表
                    await conn.execute("DELETE FROM cache_messages")
                    
                    # 然后清空缓存表
                    await conn.execute("DELETE FROM chat_caches")
                    
                    # 重置序列
                    await conn.execute("ALTER SEQUENCE cache_messages_id_seq RESTART WITH 1")
                    await conn.execute("ALTER SEQUENCE chat_caches_id_seq RESTART WITH 1")
                    
                return True
        except Exception as e:
            print(f"清空缓存时出错: {e}")
            return False
            
    async def search_chat_caches(self, keyword: str, linked_session_id: Optional[int] = None,
                              limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索聊天记录
        
        Args:
            keyword: 搜索关键词
            linked_session_id: 会话ID，可选
            limit: 结果数量限制
            
        Returns:
            匹配的缓存信息和消息预览
        """
        async with self.pool.acquire() as conn:
            if linked_session_id:
                rows = await conn.fetch('''
                SELECT DISTINCT c.id, c.linked_session_id, c.model, c.created_at, c.last_used,
                       (SELECT COUNT(*) FROM cache_messages WHERE cache_id = c.id) as message_count,
                       (SELECT content FROM cache_messages 
                        WHERE cache_id = c.id AND content ILIKE $1 
                        ORDER BY sequence_number LIMIT 1) as matched_content
                FROM chat_caches c
                JOIN cache_messages m ON c.id = m.cache_id
                WHERE m.content ILIKE $1 AND c.linked_session_id = $2
                ORDER BY c.last_used DESC
                LIMIT $3
                ''', f"%{keyword}%", linked_session_id, limit)
            else:
                rows = await conn.fetch('''
                SELECT DISTINCT c.id, c.linked_session_id, c.model, c.created_at, c.last_used,
                       (SELECT COUNT(*) FROM cache_messages WHERE cache_id = c.id) as message_count,
                       (SELECT content FROM cache_messages 
                        WHERE cache_id = c.id AND content ILIKE $1 
                        ORDER BY sequence_number LIMIT 1) as matched_content
                FROM chat_caches c
                JOIN cache_messages m ON c.id = m.cache_id
                WHERE m.content ILIKE $1
                ORDER BY c.last_used DESC
                LIMIT $2
                ''', f"%{keyword}%", limit)
            
            result = []
            for row in rows:
                item = dict(row)
                preview = item.pop('matched_content', '')
                item['preview'] = preview[:100] + ('...' if len(preview) > 100 else '') if preview else ''
                result.append(item)
                
            return result
    
    async def find_caches_by_session(self, session_id: int, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        查找与特定会话关联的所有缓存
        
        Args:
            session_id: 微信会话ID
            limit: 返回结果数量限制
            offset: 分页偏移量
            
        Returns:
            关联到指定会话的缓存列表
        """
        return await self.list_chat_caches(linked_session_id=session_id, limit=limit, offset=offset)
    
    async def import_from_json(self, json_path: str) -> Optional[int]:
        """
        从JSON文件导入会话
        
        Args:
            json_path: JSON文件路径
            
        Returns:
            导入的cache_id或None
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 提取所需字段
            model = data.get('model', 'unknown')
            api_type = data.get('model', '').startswith('grok') and 'xai' or 'openai'
            
            # 从usage中提取token计数
            usage = data.get('usage', {})
            token_count = usage.get('total_tokens', 0)
            
            # 提取消息
            messages = data.get('messages', [])
            
            # 提取系统提示词
            system_prompt = next((msg['content'] for msg in messages 
                                 if msg['role'] == 'system'), "")
            
            # 保存到数据库
            return await self.save_chat_cache(
                linked_session_id=None,  # 导入的JSON通常不包含linked_session_id
                model=model,
                api_type=api_type,
                temperature=0.7,  # 默认值
                system_prompt=system_prompt,
                messages=messages,
                token_count=token_count
            )
        except Exception as e:
            print(f"导入JSON时出错: {e}")
            return None
    
    async def export_to_json(self, cache_id: int, json_path: Optional[str] = None) -> Optional[str]:
        """
        将缓存导出为JSON
        
        Args:
            cache_id: 聊天缓存ID
            json_path: 导出路径，可选
            
        Returns:
            导出的文件路径或None
        """
        cache_data = await self.get_chat_cache(cache_id)
        if not cache_data:
            return None
            
        # 构建导出数据
        export_data = {
            'model': cache_data['model'],
            'created': str(cache_data['created_at']),
            'usage': {
                'total_tokens': cache_data['token_count']
            },
            'messages': [
                {'role': msg['role'], 'message_id': msg['message_id'], 'content': msg['content']}
                for msg in cache_data['messages']
            ]
        }
        
        # 确定导出路径
        if not json_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs('chat_exports', exist_ok=True)
            json_path = f"chat_exports/chat_{cache_id}_{timestamp}.json"
            
        # 写入文件
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            return json_path
        except Exception as e:
            print(f"导出JSON时出错: {e}")
            return None
    
    async def close(self):
        """关闭数据库连接"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            
    async def __aenter__(self):
        """支持异步with语句"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步with语句结束时关闭连接"""
        await self.close()
            
    async def create_or_update_chat_cache(self, system_prompt: str, messages: List[Dict[str, Any]], 
                                      model: str, api_type: str, temperature: float = 0.7,
                                      linked_session_id: Optional[int] = None) -> int:
        """
        创建或更新聊天缓存，如果有相同系统提示和会话ID的缓存则更新，否则创建新缓存
        
        Args:
            system_prompt: 系统提示(模板名称)
            messages: 消息列表
            model: 模型名称
            api_type: API类型
            temperature: 温度参数
            linked_session_id: 关联的会话ID
            
        Returns:
            缓存ID
        """
        async with self.pool.acquire() as conn:
            # 尝试查找匹配的现有缓存
            cache_id = None
            if linked_session_id:
                # 查找相同会话ID和系统提示的最新缓存
                row = await conn.fetchrow('''
                SELECT id FROM chat_caches
                WHERE linked_session_id = $1 AND system_prompt = $2
                ORDER BY last_used DESC
                LIMIT 1
                ''', linked_session_id, system_prompt)
                
                if row:
                    cache_id = row['id']
        
            # 计算token数（简单估算）
            token_count = 0
            for msg in messages:
                content = msg.get('content', '')
                # 简单估算：英文按单词计算，中文按字符计算，平均每4个字符约1个token
                token_count += len(content) // 4
            
            # 如果找到匹配的缓存，更新它
            if cache_id:
                await self.update_chat_cache(cache_id, messages, token_count)
                return cache_id
            
            # 否则创建新缓存
            return await self.save_chat_cache(
                linked_session_id=linked_session_id,
                model=model,
                api_type=api_type,
                temperature=temperature,
                system_prompt=system_prompt,
                messages=messages,
                token_count=token_count
            )

    async def save_chat_with_wx_references(self, linked_session_id: int, model: str, api_type: str,
                                       temperature: float, system_prompt: str, 
                                       wx_message_ids: List[int], ai_messages: List[Dict[str, str]],
                                       token_count: int = 0) -> int:
        """
        保存聊天缓存，使用微信消息ID引用
        
        Args:
            linked_session_id: 关联的微信会话ID
            model: 使用的模型名称
            api_type: API类型（如openai、xai等）
            temperature: 模型温度参数
            system_prompt: 模板名称
            wx_message_ids: 微信消息ID列表
            ai_messages: AI消息列表，格式为[{"role": "assistant", "content": "内容", "raw_response": "原始响应", "parsed_response": "解析响应", "status_code": "状态码"}]
            token_count: 总token数，默认为0
            
        Returns:
            新增的cache_id
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # 1. 插入聊天缓存
                now = datetime.now()  # 使用datetime对象而非字符串
                cache_id = await conn.fetchval('''
                INSERT INTO chat_caches 
                (linked_session_id, model, api_type, temperature, system_prompt, created_at, last_used, token_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                ''', 
                linked_session_id, model, api_type, temperature, system_prompt,
                now, now, token_count)
                
                # 2. 插入系统消息
                await conn.execute('''
                INSERT INTO cache_messages
                (cache_id, role, message_id, content, sequence_number, is_wx_message, raw_response, parsed_response, status_code)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ''', 
                cache_id, "system", None, system_prompt, 0, False, None, None, None)
                
                # 3. 插入微信消息引用
                sequence = 1
                for msg_id in wx_message_ids:
                    await conn.execute('''
                    INSERT INTO cache_messages
                    (cache_id, role, message_id, content, sequence_number, is_wx_message, raw_response, parsed_response, status_code)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ''', 
                    cache_id, "user", msg_id, "", sequence, True, None, None, None)
                    sequence += 1
                
                # 4. 插入AI消息
                for msg in ai_messages:
                    await conn.execute('''
                    INSERT INTO cache_messages
                    (cache_id, role, message_id, content, sequence_number, is_wx_message, raw_response, parsed_response, status_code)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ''', 
                    cache_id, msg.get('role', 'assistant'), None, msg.get('content', ''), 
                    sequence, False, msg.get('raw_response'), msg.get('parsed_response'), msg.get('status_code'))
                    sequence += 1
                
                return cache_id
    
    async def restore_client_with_history(self, cache_id: int, chat_tool = None, db_tool = None) -> Dict[str, Any]:
        """
        从缓存还原完整的客户端配置和消息历史
        
        Args:
            cache_id: 缓存ID
            chat_tool: 可选的ChatTool实例，如果提供则直接配置该实例
            db_tool: 可选的DBTool实例，用于获取微信消息内容
            
        Returns:
            包含完整客户端配置和消息历史的字典
        """
        # 获取客户端配置
        config = await self.get_client_config(cache_id)
        if not config:
            return {"success": False, "message": "找不到指定的缓存记录"}
            
        # 获取缓存完整信息，包括消息
        cache_data = await self.get_chat_cache(cache_id, db_tool)
        if not cache_data:
            return {"success": False, "message": "找不到指定的缓存记录"}
            
        # 构建消息历史，确保格式正确
        messages = []
        for msg in cache_data['messages']:
            # 跳过空消息
            if not msg.get('content') and not msg.get('message_id'):
                continue
                
            # 构建消息对象
            message = {
                "role": msg['role'],
                "content": msg['content'] or ""
            }
            messages.append(message)
            
        # 如果提供了ChatTool实例，直接配置它
        if chat_tool:
            # 配置聊天工具(假设ChatTool有这些方法)
            try:
                # 创建一个新的配置或使用现有配置
                custom_config = {
                    "api_type": config.get('api_type', 'openai'),
                    "model": config.get('model', 'gpt-3.5-turbo'),
                    "temperature": config.get('temperature', 0.7),
                    "default_template": config.get('template', 'default')
                }
                
                # 配置聊天工具(这里需要根据ChatTool的实际API调整)
                # 假设ChatTool有set_config方法
                if hasattr(chat_tool, 'set_config'):
                    chat_tool.set_config(custom_config)
                
                # 假设ChatTool有set_history方法
                if hasattr(chat_tool, 'set_history'):
                    chat_tool.set_history(messages)
            except Exception as e:
                return {
                    "success": False, 
                    "message": f"配置ChatTool实例失败: {str(e)}",
                    "config": config,
                    "messages": messages
                }
                
            return {
                "success": True,
                "message": "成功配置ChatTool实例",
                "chat_tool": chat_tool,
                "config": config,
                "messages": messages
            }
        
        # 否则仅返回配置和消息历史
        return {
            "success": True,
            "message": "成功获取客户端配置和历史记录",
            "config": config,
            "messages": messages,
            "linked_session_id": cache_data['linked_session_id'],
            "token_count": cache_data['token_count']
        }


# 示例使用方法
async def example_usage():
    """PostgresCacheTool使用示例"""
    # 创建PostgreSQL工具实例
    cache_tool = PostgresCacheTool(
        user='postgres',
        password='YOUR_DATABASE_PASSWORD_HERE',
        database='postgres',
        host='localhost',
        port=5432
    )
    
    try:
        # 连接数据库
        await cache_tool.connect()
        
        # 创建一个测试缓存
        messages = [
            {"role": "system", "content": "你是一个AI助手，请帮助用户回答问题。"},
            {"role": "user", "content": "你好，请介绍一下PostgreSQL数据库"},
            {"role": "assistant", "content": "PostgreSQL是一个功能强大的开源关系型数据库系统..."}
        ]
        
        cache_id = await cache_tool.save_chat_cache(
            linked_session_id=None,
            model="gpt-3.5-turbo",
            api_type="openai",
            temperature=0.7,
            system_prompt="general_assistant",
            messages=messages,
            token_count=150
        )
        
        print(f"创建了一个新的缓存，ID: {cache_id}")
        
        # 获取缓存信息
        cache_info = await cache_tool.get_chat_cache(cache_id)
        print(f"缓存信息: {cache_info}")
        
    finally:
        # 关闭连接
        await cache_tool.close()


# 如果直接运行此脚本，执行示例
if __name__ == "__main__":
    asyncio.run(example_usage())
