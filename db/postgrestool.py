import asyncio
import asyncpg
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import json


class PostgresTool:
    """微信会话数据库工具类，基于PostgreSQL的异步实现"""
    
    def __init__(self, 
                user: str = 'YOUR_DATABASE_USER_HERE',
                password: str = 'YOUR_DATABASE_PASSWORD_HERE',
                database: str = 'postgres',
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
        self.session_map = {}  # 缓存会话名称到ID的映射
        
    async def connect(self):
        """连接到数据库"""
        try:
            self.pool = await asyncpg.create_pool(**self.conn_params)
            # 如果是新数据库，初始化表结构
            await self._check_and_init_db()
            # 加载现有会话映射
            await self._load_existing_sessions()
            return True
        except Exception as e:
            print(f"连接数据库失败: {e}")
            return False
    
    async def _check_and_init_db(self):
        """检查并初始化数据库表结构"""
        async with self.pool.acquire() as conn:
            try:
                # 检查sessions表是否存在
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = 'sessions'
                    )
                """)
                
                if not exists:
                    # 数据库表不存在，初始化数据库
                    await self._init_db(conn)
                else:
                    # 表存在，检查消息表中是否有session_id字段
                    has_session_id = await conn.fetchval("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.columns
                            WHERE table_schema = 'public' 
                              AND table_name = 'messages'
                              AND column_name = 'session_id'
                        )
                    """)
                    
                    if not has_session_id:
                        # 如果消息表存在但缺少session_id字段，可能是旧版表结构
                        # 重新初始化数据库
                        print("消息表缺少session_id字段，重新初始化表结构...")
                        await self._drop_tables(conn)
                        await self._init_db(conn)
            except Exception as e:
                print(f"检查数据库结构时出错: {e}")
                # 出错时尝试创建表
                await self._init_db(conn)
    
    async def _drop_tables(self, conn):
        """删除现有表"""
        try:
            # 使用事务确保原子操作
            async with conn.transaction():
                # 先删除messages表（因为有外键约束）
                await conn.execute("DROP TABLE IF EXISTS messages")
                # 再删除sessions表
                await conn.execute("DROP TABLE IF EXISTS sessions")
        except Exception as e:
            print(f"删除表失败: {e}")
            # 错误会被外部捕获处理
            raise
    
    async def _init_db(self, conn):
        """初始化数据库表结构"""
        try:
            # 使用事务确保原子操作
            async with conn.transaction():
                # 创建会话表
                await conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
                
                # 创建消息表
                await conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    sender TEXT,
                    content TEXT NOT NULL,
                    msg_type TEXT NOT NULL,
                    sequence_number INTEGER,
                    raw_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
                
                # 创建索引
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_msg_type ON messages(msg_type)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_msg_sequence ON messages(sequence_number)')
                
                print("数据库表结构初始化成功")
        except Exception as e:
            print(f"初始化数据库表结构失败: {e}")
            raise
    
    async def _load_existing_sessions(self):
        """加载已有会话到缓存"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT id, name FROM sessions')
            self.session_map = {name: sid for sid, name in rows}
    
    #-------------------------------------------------------------------------
    # 会话相关操作
    #-------------------------------------------------------------------------
    
    async def get_session_id(self, session_name: str) -> int:
        """
        获取会话ID，如果不存在则创建
        
        Args:
            session_name: 会话名称
            
        Returns:
            会话ID
        """
        session_name = session_name.strip()
        if session_name not in self.session_map:
            async with self.pool.acquire() as conn:
                # 尝试插入会话
                try:
                    session_id = await conn.fetchval(
                        'INSERT INTO sessions (name) VALUES ($1) ON CONFLICT (name) DO NOTHING RETURNING id',
                        session_name
                    )
                    
                    # 如果没有返回ID（已存在），则查询现有会话ID
                    if session_id is None:
                        session_id = await conn.fetchval(
                            'SELECT id FROM sessions WHERE name = $1',
                            session_name
                        )
                    
                    self.session_map[session_name] = session_id
                except Exception as e:
                    print(f"创建或获取会话ID失败: {e}")
                    raise
        
        return self.session_map[session_name]
    
    async def get_sessions(self) -> List[Dict[str, Any]]:
        """
        获取所有会话列表
        
        Returns:
            会话列表，每个会话包含id、name、message_count
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
            SELECT 
                s.id, 
                s.name, 
                COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id, s.name
            ORDER BY s.id DESC
            ''')
            
            return [dict(row) for row in rows]
    
    async def get_session_by_name(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取会话
        
        Args:
            session_name: 会话名称
            
        Returns:
            会话信息或None（如果不存在）
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
            SELECT 
                s.id, 
                s.name, 
                COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            WHERE s.name = $1
            GROUP BY s.id, s.name
            ''', session_name)
            
            return dict(row) if row else None
    
    async def get_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话信息或None（如果不存在）
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
            SELECT 
                s.id, 
                s.name, 
                COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            WHERE s.id = $1
            GROUP BY s.id, s.name
            ''', session_id)
            
            return dict(row) if row else None
    
    async def delete_session(self, session_id: int) -> bool:
        """
        删除会话及其所有消息
        
        Args:
            session_id: 会话ID
            
        Returns:
            操作是否成功
        """
        try:
            async with self.pool.acquire() as conn:
                # 使用事务确保原子操作
                async with conn.transaction():
                    # 先删除会话的所有消息
                    await conn.execute("DELETE FROM messages WHERE session_id = $1", session_id)
                    # 再删除会话本身
                    await conn.execute("DELETE FROM sessions WHERE id = $1", session_id)
                
                # 更新缓存
                session_to_remove = None
                for name, sid in self.session_map.items():
                    if sid == session_id:
                        session_to_remove = name
                        break
                        
                if session_to_remove:
                    del self.session_map[session_to_remove]
                
                return True
        except Exception as e:
            print(f"删除会话失败: {e}")
            return False
            
    async def delete_all_sessions(self) -> bool:
        """
        删除所有会话和消息（清空数据库）
        
        Returns:
            操作是否成功
        """
        try:
            async with self.pool.acquire() as conn:
                # 使用事务确保原子操作
                async with conn.transaction():
                    # 清空所有表数据
                    await conn.execute("DELETE FROM messages")
                    await conn.execute("DELETE FROM sessions")
                    
                    # 重置序列
                    await conn.execute("ALTER SEQUENCE messages_id_seq RESTART WITH 1")
                    await conn.execute("ALTER SEQUENCE sessions_id_seq RESTART WITH 1")
                
                # 更新缓存
                self.session_map = {}
                return True
        except Exception as e:
            print(f"清空数据库失败: {e}")
            return False
    
    #-------------------------------------------------------------------------
    # 消息相关操作
    #-------------------------------------------------------------------------
    
    async def add_message(self, session_id: int, sender: Optional[str], content: str, 
                        msg_type: str, raw_data: Optional[str] = None,
                        sequence_number: Optional[int] = None) -> int:
        """
        添加一条消息
        
        Args:
            session_id: 会话ID
            sender: 发送者，可为None
            content: 消息内容
            msg_type: 消息类型
            raw_data: 原始数据，可为None
            sequence_number: 消息顺序号，可为None（自动计算）
            
        Returns:
            新增消息的ID
        """
        async with self.pool.acquire() as conn:
            # 如果未提供sequence_number，则自动计算
            if sequence_number is None:
                # 获取当前会话中消息的最大序号
                max_seq = await conn.fetchval(
                    'SELECT MAX(sequence_number) FROM messages WHERE session_id = $1',
                    session_id
                )
                sequence_number = 1 if max_seq is None else max_seq + 1
                
            # 插入消息
            message_id = await conn.fetchval('''
            INSERT INTO messages 
            (session_id, sender, content, msg_type, raw_data, sequence_number)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            ''', session_id, sender, content, msg_type, raw_data, sequence_number)
            
            return message_id
    
    async def get_messages(self, session_id: int, limit: int = 50, offset: int = 0,
                         order_by: str = "sequence_number") -> List[Dict[str, Any]]:
        """
        获取会话消息
        
        Args:
            session_id: 会话ID
            limit: 限制返回条数
            offset: 偏移量（分页用）
            order_by: 排序字段，默认为sequence_number
            
        Returns:
            消息列表
        """
        async with self.pool.acquire() as conn:
            # 构建排序子句
            order_clause = order_by if order_by in ["id", "sequence_number", "created_at"] else "sequence_number"
            
            # 构建查询
            query = f"""
            SELECT id, sender, content, msg_type, sequence_number, created_at
            FROM messages
            WHERE session_id = $1
            ORDER BY {order_clause}
            LIMIT $2 OFFSET $3
            """
            
            rows = await conn.fetch(query, session_id, limit, offset)
            
            # 处理结果
            return [dict(row) for row in rows]
    
    async def search_messages(self, keyword: str, session_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        搜索消息
        
        Args:
            keyword: 关键词
            session_id: 会话ID，可选
            
        Returns:
            匹配的消息列表
        """
        async with self.pool.acquire() as conn:
            if session_id:
                query = """
                SELECT 
                    m.id,
                    s.name as session_name,
                    m.sender,
                    m.content,
                    m.msg_type,
                    m.sequence_number
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.session_id = $1 AND m.content ILIKE $2
                ORDER BY m.sequence_number DESC
                LIMIT 100
                """
                rows = await conn.fetch(query, session_id, f"%{keyword}%")
            else:
                query = """
                SELECT 
                    m.id,
                    s.name as session_name,
                    m.sender,
                    m.content,
                    m.msg_type,
                    m.sequence_number
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.content ILIKE $1
                ORDER BY s.name, m.sequence_number DESC
                LIMIT 100
                """
                rows = await conn.fetch(query, f"%{keyword}%")
            
            # 处理结果
            return [dict(row) for row in rows]
    
    async def get_messages_by_session_id(self, session_id: int) -> List[Dict[str, Any]]:
        """
        获取指定会话的所有消息
        
        Args:
            session_id: 会话ID
            
        Returns:
            所有消息的列表，按照创建时间或序号排序
        """
        async with self.pool.acquire() as conn:
            query = """
            SELECT 
                id, 
                sender, 
                content, 
                msg_type, 
                sequence_number, 
                created_at
            FROM messages
            WHERE session_id = $1
            ORDER BY created_at, sequence_number
            """
            
            rows = await conn.fetch(query, session_id)
            
            # 处理结果
            return [dict(row) for row in rows]
    
    async def get_messages_by_session_name(self, session_name: str) -> List[Dict[str, Any]]:
        """
        根据会话名称获取所有消息
        
        Args:
            session_name: 会话名称
            
        Returns:
            所有消息的列表，按照创建时间或序号排序
        """
        # 先获取会话ID
        session = await self.get_session_by_name(session_name)
        if not session:
            return []  # 会话不存在则返回空列表
            
        # 调用现有方法获取消息
        return await self.get_messages_by_session_id(session['id'])
    
    #-------------------------------------------------------------------------
    # 实用方法
    #-------------------------------------------------------------------------
    
    async def close(self):
        """关闭数据库连接池"""
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


# 示例使用方法
async def example_usage():
    # 创建PostgreSQL工具实例
    db = PostgresTool(
        user='postgres',
        password='YOUR_DATABASE_PASSWORD_HERE',
        database='postgres',
        host='localhost',
        port=5432
    )
    
    try:
        # 连接数据库
        await db.connect()
        
        # 创建一个会话
        session_name = "测试会话"
        session_id = await db.get_session_id(session_name)
        
        # 添加一些消息
        await db.add_message(
            session_id=session_id,
            sender="用户",
            content="你好，这是一条测试消息",
            msg_type="text"
        )
        
        await db.add_message(
            session_id=session_id,
            sender="系统",
            content="这是系统响应消息",
            msg_type="text"
        )
        
        # 获取所有会话
        sessions = await db.get_sessions()
        print(f"会话列表: {sessions}")
        
        # 获取会话消息(通过ID)
        messages = await db.get_messages(session_id)
        print(f"通过ID获取消息列表: {messages}")
        
        # 通过会话名称获取所有消息
        messages_by_name = await db.get_messages_by_session_name(session_name)
        print(f"通过会话名称获取消息列表: {messages_by_name}")
        
    finally:
        # 关闭连接
        await db.close()


# 如果直接运行此脚本，执行示例
if __name__ == "__main__":
    asyncio.run(example_usage())
