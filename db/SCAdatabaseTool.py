import asyncio
import asyncpg
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import json
import pathlib
import re


class SCAdatabaseTool:
    """SCA自动化数据库工具类，基于PostgreSQL的异步实现"""
    
    def __init__(self, 
                user: str = 'YOUR_DATABASE_USER_HERE',
                password: str = 'YOUR_DATABASE_PASSWORD_HERE',
                database: str = 'sca_db',
                host: str = 'YOUR_DATABASE_HOST_HERE',
                port: int = 5432  # Change to YOUR_DATABASE_PORT_HERE):
        """
        初始化PostgreSQL数据库工具
        
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
        self.chat_map = {}  # 缓存聊天名称到ID的映射
        
    async def connect(self):
        """连接到数据库"""
        try:
            self.pool = await asyncpg.create_pool(**self.conn_params)
            # 如果是新数据库，初始化表结构
            await self._check_and_init_db()
            # 加载现有聊天映射
            await self._load_existing_chats()
            return True
        except Exception as e:
            print(f"连接数据库失败: {e}")
            return False
            
    async def _check_and_init_db(self):
        """检查并初始化数据库表结构"""
        async with self.pool.acquire() as conn:
            try:
                # 检查chats表是否存在
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = 'chats'
                    )
                """)
                
                if not exists:
                    # 数据库表不存在，初始化数据库
                    await self._init_db(conn)
                else:
                    # 表存在，检查是否有新增表
                    has_comments = await conn.fetchval("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_schema = 'public' 
                              AND table_name = 'xiaohongshu_comments'
                        )
                    """)
                    
                    has_strangers = await conn.fetchval("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_schema = 'public' 
                              AND table_name = 'stranger_messages'
                        )
                    """)
                    
                    if not has_comments or not has_strangers:
                        # 如果缺少新表，则创建它们
                        print("检测到缺少部分表，正在创建...")
                        if not has_comments:
                            await self._create_comment_tables(conn)
                        if not has_strangers:
                            await self._create_stranger_tables(conn)
            except Exception as e:
                print(f"检查数据库结构时出错: {e}")
                # 出错时尝试创建表
                await self._init_db(conn)
                
    async def _init_db(self, conn):
        """初始化数据库表结构"""
        try:
            # 使用事务确保原子操作
            async with conn.transaction():
                # 创建聊天表
                await self._create_chat_tables(conn)
                
                # 创建评论表
                await self._create_comment_tables(conn)
                
                # 创建陌生人消息表
                await self._create_stranger_tables(conn)
                
                print("数据库表结构初始化成功")
        except Exception as e:
            print(f"初始化数据库表结构失败: {e}")
            raise
            
    async def _create_chat_tables(self, conn):
        """创建聊天相关表结构"""
        # 创建聊天表
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            app_type TEXT NOT NULL,
            is_group BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, app_type)
        )''')
        
        # 创建聊天历史记录表
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_histories (
            id SERIAL PRIMARY KEY,
            chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
            collection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_group BOOLEAN DEFAULT false,
            online_count INTEGER,
            total_members INTEGER,
            message_count INTEGER DEFAULT 0,
            stats JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # 创建消息表
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            history_id INTEGER NOT NULL REFERENCES chat_histories(id) ON DELETE CASCADE,
            sender TEXT,
            is_self BOOLEAN DEFAULT false,
            content TEXT NOT NULL,
            msg_type TEXT NOT NULL,
            timestamp TEXT,
            raw_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # 创建索引
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_name ON chats(name)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_app ON chats(app_type)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_history_chat ON chat_histories(chat_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_msg_history ON messages(history_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_msg_type ON messages(msg_type)')
        
    async def _create_comment_tables(self, conn):
        """创建评论相关表结构"""
        # 创建小红书评论表
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS xiaohongshu_comments (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            comment_type TEXT,
            time TEXT,
            content TEXT NOT NULL,
            reply_content TEXT,
            quoted_content TEXT,
            is_quote_reply BOOLEAN DEFAULT false,
            is_deleted BOOLEAN DEFAULT false,
            has_like BOOLEAN DEFAULT false,
            has_reply BOOLEAN DEFAULT false,
            has_emoji BOOLEAN DEFAULT false,
            is_fan BOOLEAN DEFAULT false,
            batch INTEGER,
            collection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_data JSONB
        )''')
        
        # 创建索引
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_xhs_comment_user ON xiaohongshu_comments(username)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_xhs_comment_time ON xiaohongshu_comments(collection_time)')
        
    async def _create_stranger_tables(self, conn):
        """创建陌生人消息相关表结构"""
        # 创建陌生人消息表
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS stranger_messages (
            id SERIAL PRIMARY KEY,
            chat_name TEXT NOT NULL,
            message_type TEXT NOT NULL,
            content TEXT NOT NULL,
            time TEXT,
            platform TEXT DEFAULT 'xiaohongshu',
            is_read BOOLEAN DEFAULT false,
            collection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_data JSONB
        )''')
        
        # 创建索引
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_stranger_chat ON stranger_messages(chat_name)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_stranger_time ON stranger_messages(collection_time)')

    async def _load_existing_chats(self):
        """加载已有会话到缓存"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT id, name, app_type FROM chats')
            self.chat_map = {f"{name}:{app_type}": chat_id for chat_id, name, app_type in rows}
            
    #-------------------------------------------------------------------------
    # 聊天相关操作
    #-------------------------------------------------------------------------
    
    async def get_chat_id(self, chat_name: str, app_type: str = 'xiaohongshu', is_group: bool = False) -> int:
        """
        获取聊天ID，如果不存在则创建
        
        Args:
            chat_name: 聊天名称
            app_type: 应用类型，默认为xiaohongshu
            is_group: 是否群聊
            
        Returns:
            聊天ID
        """
        # 生成缓存键
        cache_key = f"{chat_name}:{app_type}"
        
        # 检查缓存
        if cache_key in self.chat_map:
            return self.chat_map[cache_key]
            
        # 缓存中不存在，访问数据库
        async with self.pool.acquire() as conn:
            # 尝试获取现有ID
            chat_id = await conn.fetchval(
                'SELECT id FROM chats WHERE name = $1 AND app_type = $2',
                chat_name, app_type
            )
            
            if chat_id is None:
                # 不存在，创建新聊天
                chat_id = await conn.fetchval('''
                INSERT INTO chats (name, app_type, is_group, last_updated) 
                VALUES ($1, $2, $3, $4)
                RETURNING id
                ''', chat_name, app_type, is_group, datetime.now())
            else:
                # 更新最后更新时间
                await conn.execute(
                    'UPDATE chats SET last_updated = $1 WHERE id = $2',
                    datetime.now(), chat_id
                )
            
            # 更新缓存
            self.chat_map[cache_key] = chat_id
            return chat_id
    
    async def add_chat_history(self, chat_id: int, collection_time: Optional[datetime] = None, 
                            is_group: bool = False, online_count: Optional[int] = None, 
                            total_members: Optional[int] = None, message_count: int = 0, 
                            stats: Optional[Dict[str, Any]] = None) -> int:
        """
        添加聊天历史记录
        
        Args:
            chat_id: 聊天ID
            collection_time: 收集时间，默认为当前时间
            is_group: 是否群聊
            online_count: 在线人数
            total_members: 总成员数
            message_count: 消息数量
            stats: 统计信息
            
        Returns:
            历史记录ID
        """
        if collection_time is None:
            collection_time = datetime.now()
            
        if stats is not None and not isinstance(stats, str):
            stats = json.dumps(stats)
            
        async with self.pool.acquire() as conn:
            history_id = await conn.fetchval('''
            INSERT INTO chat_histories 
            (chat_id, collection_time, is_group, online_count, total_members, message_count, stats)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            ''', chat_id, collection_time, is_group, online_count, total_members, message_count, stats)
            
            return history_id
    
    async def add_message(self, history_id: int, sender: Optional[str] = None, 
                      is_self: bool = False, content: str = '', 
                      msg_type: str = 'text', timestamp: Optional[str] = None, 
                      raw_data: Optional[Dict[str, Any]] = None) -> int:
        """
        添加聊天消息
        
        Args:
            history_id: 历史记录ID
            sender: 发送者
            is_self: 是否自己发送
            content: 消息内容
            msg_type: 消息类型
            timestamp: 时间戳
            raw_data: 原始数据
            
        Returns:
            消息ID
        """
        if raw_data is not None and not isinstance(raw_data, str):
            raw_data = json.dumps(raw_data)
            
        async with self.pool.acquire() as conn:
            # 添加消息
            message_id = await conn.fetchval('''
            INSERT INTO messages 
            (history_id, sender, is_self, content, msg_type, timestamp, raw_data)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            ''', history_id, sender, is_self, content, msg_type, timestamp, raw_data)
            
            # 更新历史记录中的消息数量
            await conn.execute('''
            UPDATE chat_histories 
            SET message_count = message_count + 1
            WHERE id = $1
            ''', history_id)
            
            return message_id
    
    async def add_messages(self, history_id: int, messages: List[Dict[str, Any]]) -> int:
        """
        批量添加聊天消息
        
        Args:
            history_id: 历史记录ID
            messages: 消息列表
            
        Returns:
            添加的消息数量
        """
        if not messages:
            return 0
            
        count = 0
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for message in messages:
                    try:
                        sender = message.get('sender')
                        is_self = message.get('is_self', False)
                        content = message.get('content', '')
                        msg_type = message.get('msg_type', 'text')
                        timestamp = message.get('timestamp')
                        raw_data = message.get('raw_data')
                        
                        if raw_data is not None and not isinstance(raw_data, str):
                            raw_data = json.dumps(raw_data)
                        
                        # 添加消息
                        await conn.execute('''
                        INSERT INTO messages 
                        (history_id, sender, is_self, content, msg_type, timestamp, raw_data)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ''', history_id, sender, is_self, content, msg_type, timestamp, raw_data)
                        
                        count += 1
                    except Exception as e:
                        print(f"插入消息失败: {e}")
                        # 继续处理下一条消息
                
                # 更新历史记录中的消息数量
                await conn.execute('''
                UPDATE chat_histories 
                SET message_count = message_count + $1
                WHERE id = $2
                ''', count, history_id)
        
        return count
    
    async def get_chat_by_name(self, chat_name: str, app_type: str = 'xiaohongshu') -> Optional[Dict[str, Any]]:
        """
        根据名称获取聊天
        
        Args:
            chat_name: 聊天名称
            app_type: 应用类型
            
        Returns:
            聊天信息或None
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
            SELECT * FROM chats
            WHERE name = $1 AND app_type = $2
            ''', chat_name, app_type)
            
            return dict(row) if row else None
            
    #-------------------------------------------------------------------------
    # 评论相关操作
    #-------------------------------------------------------------------------
    
    async def add_xiaohongshu_comment(self, comment_data: Dict[str, Any]) -> int:
        """
        添加小红书评论
        
        Args:
            comment_data: 评论数据，包含username, content等字段
            
        Returns:
            新增评论的ID
        """
        async with self.pool.acquire() as conn:
            # 构建SQL语句和参数
            fields = []
            placeholders = []
            values = []
            
            # 遍历评论数据
            for i, (key, value) in enumerate(comment_data.items(), 1):
                if key in ['username', 'comment_type', 'time', 'content', 'reply_content', 
                         'quoted_content', 'is_quote_reply', 'is_deleted', 'has_like', 
                         'has_reply', 'has_emoji', 'is_fan', 'batch', 'raw_data']:
                    fields.append(key)
                    placeholders.append(f'${i}')
                    
                    # 对原始数据进行JSON序列化
                    if key == 'raw_data' and value and not isinstance(value, str):
                        value = json.dumps(value)
                    
                    values.append(value)
            
            # 添加收集时间
            fields.append('collection_time')
            placeholders.append(f'${len(values) + 1}')
            values.append(datetime.now())
            
            # 执行插入操作
            query = f'''
            INSERT INTO xiaohongshu_comments 
            ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            RETURNING id
            '''
            
            comment_id = await conn.fetchval(query, *values)
            return comment_id
            
    async def add_xiaohongshu_comments(self, comments: List[Dict[str, Any]]) -> int:
        """
        批量添加小红书评论
        
        Args:
            comments: 评论列表
            
        Returns:
            添加的评论数量
        """
        if not comments:
            return 0
            
        count = 0
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for comment in comments:
                    try:
                        # 构建SQL语句和参数
                        fields = []
                        placeholders = []
                        values = []
                        
                        # 遍历评论数据
                        for i, (key, value) in enumerate(comment.items(), 1):
                            if key in ['username', 'comment_type', 'time', 'content', 'reply_content', 
                                     'quoted_content', 'is_quote_reply', 'is_deleted', 'has_like', 
                                     'has_reply', 'has_emoji', 'is_fan', 'batch', 'raw_data']:
                                fields.append(key)
                                placeholders.append(f'${i}')
                                
                                # 对原始数据进行JSON序列化
                                if key == 'raw_data' and value and not isinstance(value, str):
                                    value = json.dumps(value)
                                
                                values.append(value)
                        
                        # 添加收集时间
                        fields.append('collection_time')
                        placeholders.append(f'${len(values) + 1}')
                        values.append(datetime.now())
                        
                        # 执行插入操作
                        query = f'''
                        INSERT INTO xiaohongshu_comments 
                        ({', '.join(fields)})
                        VALUES ({', '.join(placeholders)})
                        '''
                        
                        await conn.execute(query, *values)
                        count += 1
                    except Exception as e:
                        print(f"插入评论失败: {e}")
                        # 继续处理下一条评论
        
        return count
        
    async def get_xiaohongshu_comments(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取小红书评论
        
        Args:
            limit: 限制条数
            offset: 偏移量（分页）
            
        Returns:
            评论列表
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
            SELECT * FROM xiaohongshu_comments
            ORDER BY collection_time DESC, id DESC
            LIMIT $1 OFFSET $2
            ''', limit, offset)
            
            return [dict(row) for row in rows]
            
    async def get_xiaohongshu_comments_by_username(self, username: str) -> List[Dict[str, Any]]:
        """
        根据用户名获取小红书评论
        
        Args:
            username: 用户名
            
        Returns:
            评论列表
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
            SELECT * FROM xiaohongshu_comments
            WHERE username = $1
            ORDER BY collection_time DESC, id DESC
            ''', username)
            
            return [dict(row) for row in rows]
            
    async def search_xiaohongshu_comments(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索小红书评论
        
        Args:
            keyword: 关键词
            
        Returns:
            匹配的评论列表
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
            SELECT * FROM xiaohongshu_comments
            WHERE 
                content ILIKE $1 OR 
                reply_content ILIKE $1 OR 
                quoted_content ILIKE $1 OR 
                username ILIKE $1
            ORDER BY collection_time DESC, id DESC
            LIMIT 100
            ''', f'%{keyword}%')
            
            return [dict(row) for row in rows]
            
    async def delete_xiaohongshu_comment(self, comment_id: int) -> bool:
        """
        删除小红书评论
        
        Args:
            comment_id: 评论ID
            
        Returns:
            是否成功
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute('''
            DELETE FROM xiaohongshu_comments
            WHERE id = $1
            ''', comment_id)
            
            # 返回是否成功删除（通过检查影响的行数）
            return 'DELETE 1' in result
            
    async def delete_xiaohongshu_comments_by_username(self, username: str) -> int:
        """
        删除指定用户的所有小红书评论
        
        Args:
            username: 用户名
            
        Returns:
            删除的评论数量
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute('''
            DELETE FROM xiaohongshu_comments
            WHERE username = $1
            ''', username)
            
            # 解析删除的行数
            match = re.search(r'DELETE (\d+)', result)
            return int(match.group(1)) if match else 0
            
    async def delete_all_xiaohongshu_comments(self) -> int:
        """
        删除所有小红书评论
        
        Returns:
            删除的评论数量
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute('DELETE FROM xiaohongshu_comments')
            
            # 解析删除的行数
            match = re.search(r'DELETE (\d+)', result)
            return int(match.group(1)) if match else 0
            
    #-------------------------------------------------------------------------
    # 陌生人消息相关操作
    #-------------------------------------------------------------------------
    
    async def add_stranger_message(self, message_data: Dict[str, Any]) -> int:
        """
        添加陌生人消息
        
        Args:
            message_data: 消息数据，包含chat_name, message_type, content等字段
            
        Returns:
            新增消息的ID
        """
        async with self.pool.acquire() as conn:
            # 构建SQL语句和参数
            fields = []
            placeholders = []
            values = []
            
            # 遍历消息数据
            for i, (key, value) in enumerate(message_data.items(), 1):
                if key in ['chat_name', 'message_type', 'content', 'time', 
                         'platform', 'is_read', 'raw_data']:
                    fields.append(key)
                    placeholders.append(f'${i}')
                    
                    # 对原始数据进行JSON序列化
                    if key == 'raw_data' and value and not isinstance(value, str):
                        value = json.dumps(value)
                    
                    values.append(value)
            
            # 添加收集时间
            fields.append('collection_time')
            placeholders.append(f'${len(values) + 1}')
            values.append(datetime.now())
            
            # 执行插入操作
            query = f'''
            INSERT INTO stranger_messages 
            ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            RETURNING id
            '''
            
            message_id = await conn.fetchval(query, *values)
            return message_id
            
    async def add_stranger_messages(self, messages: List[Dict[str, Any]]) -> int:
        """
        批量添加陌生人消息
        
        Args:
            messages: 消息列表
            
        Returns:
            添加的消息数量
        """
        if not messages:
            return 0
            
        count = 0
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for message in messages:
                    try:
                        # 构建SQL语句和参数
                        fields = []
                        placeholders = []
                        values = []
                        
                        # 遍历消息数据
                        for i, (key, value) in enumerate(message.items(), 1):
                            if key in ['chat_name', 'message_type', 'content', 'time', 
                                     'platform', 'is_read', 'raw_data']:
                                fields.append(key)
                                placeholders.append(f'${i}')
                                
                                # 对原始数据进行JSON序列化
                                if key == 'raw_data' and value and not isinstance(value, str):
                                    value = json.dumps(value)
                                
                                values.append(value)
                        
                        # 添加收集时间
                        fields.append('collection_time')
                        placeholders.append(f'${len(values) + 1}')
                        values.append(datetime.now())
                        
                        # 执行插入操作
                        query = f'''
                        INSERT INTO stranger_messages 
                        ({', '.join(fields)})
                        VALUES ({', '.join(placeholders)})
                        '''
                        
                        await conn.execute(query, *values)
                        count += 1
                    except Exception as e:
                        print(f"插入陌生人消息失败: {e}")
                        # 继续处理下一条消息
        
        return count
        
    async def get_stranger_messages(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取陌生人消息
        
        Args:
            limit: 限制条数
            offset: 偏移量（分页）
            
        Returns:
            消息列表
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
            SELECT * FROM stranger_messages
            ORDER BY collection_time DESC, id DESC
            LIMIT $1 OFFSET $2
            ''', limit, offset)
            
            return [dict(row) for row in rows]
            
    async def get_stranger_messages_by_chat_name(self, chat_name: str) -> List[Dict[str, Any]]:
        """
        根据聊天名称获取陌生人消息
        
        Args:
            chat_name: 聊天名称
            
        Returns:
            消息列表
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
            SELECT * FROM stranger_messages
            WHERE chat_name = $1
            ORDER BY collection_time DESC, id DESC
            ''', chat_name)
            
            return [dict(row) for row in rows]
            
    async def search_stranger_messages(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索陌生人消息
        
        Args:
            keyword: 关键词
            
        Returns:
            匹配的消息列表
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
            SELECT * FROM stranger_messages
            WHERE 
                content ILIKE $1 OR 
                chat_name ILIKE $1
            ORDER BY collection_time DESC, id DESC
            LIMIT 100
            ''', f'%{keyword}%')
            
            return [dict(row) for row in rows]
            
    async def delete_stranger_message(self, message_id: int) -> bool:
        """
        删除陌生人消息
        
        Args:
            message_id: 消息ID
            
        Returns:
            是否成功
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute('''
            DELETE FROM stranger_messages
            WHERE id = $1
            ''', message_id)
            
            # 返回是否成功删除
            return 'DELETE 1' in result
            
    async def delete_stranger_messages_by_chat_name(self, chat_name: str) -> int:
        """
        删除指定聊天的所有陌生人消息
        
        Args:
            chat_name: 聊天名称
            
        Returns:
            删除的消息数量
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute('''
            DELETE FROM stranger_messages
            WHERE chat_name = $1
            ''', chat_name)
            
            # 解析删除的行数
            match = re.search(r'DELETE (\d+)', result)
            return int(match.group(1)) if match else 0
            
    async def delete_all_stranger_messages(self) -> int:
        """
        删除所有陌生人消息
        
        Returns:
            删除的消息数量
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute('DELETE FROM stranger_messages')
            
            # 解析删除的行数
            match = re.search(r'DELETE (\d+)', result)
            return int(match.group(1)) if match else 0
            
    async def close(self):
        """关闭数据库连接池"""
        if self.pool:
            await self.pool.close()
            self.pool = None
  