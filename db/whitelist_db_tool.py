#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库白名单管理工具类

功能：
- 飞书商务模块的白名单管理
- 支持增删改查操作
- 批量操作支持
- 历史记录跟踪
- 数据验证和去重

支持的模块：
- larkbusiness: 飞书商务模块（唯一支持的模块）
"""

import asyncio
import asyncpg
import time
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import json
import logging


class WhitelistDBTool:
    """数据库白名单管理工具类"""
    
    def __init__(self, 
                 user: str = 'YOUR_DATABASE_USER_HERE',
                 password: str = 'YOUR_DATABASE_PASSWORD_HERE',
                 database: str = 'postgres',
                 host: str = 'YOUR_DATABASE_HOST_HERE',
                 port: int = 5432  # Change to YOUR_DATABASE_PORT_HERE):
        """
        初始化数据库白名单管理工具
        
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
            'port': port,
            # 🔧 防死锁：优化连接池配置
            'min_size': 2,      # 最小连接数
            'max_size': 10,     # 最大连接数（防止连接池耗尽）
            'command_timeout': 30,  # 命令超时30秒
            'server_settings': {
                'application_name': 'whitelist_db_tool',
                'jit': 'off'  # 关闭JIT以提高小查询性能
            }
        }
        self.pool = None
        self.logger = logging.getLogger(__name__)
        
        # 支持的模块列表（只支持larkbusiness）
        self.supported_modules = {
            'larkbusiness': '飞书商务模块'
        }
        
        # 🔧 防死锁：添加操作锁，防止并发写入冲突
        self._operation_lock = asyncio.Lock()
        self._last_operation_time = {}  # 记录每个模块的最后操作时间
    
    async def connect(self):
        """连接到数据库"""
        try:
            print(f"🔗 尝试连接PostgreSQL数据库...")
            print(f"   主机: {self.conn_params['host']}")
            print(f"   端口: {self.conn_params['port']}")
            print(f"   用户: {self.conn_params['user']}")
            print(f"   数据库: {self.conn_params['database']}")
            
            self.pool = await asyncpg.create_pool(**self.conn_params)
            
            # 测试连接
            async with self.pool.acquire() as conn:
                version = await conn.fetchval('SELECT version()')
                print(f"✅ 数据库连接成功！PostgreSQL版本: {version}")
                
            # 初始化数据库表结构
            await self._init_tables()
            return True
            
        except asyncpg.exceptions.InvalidCatalogNameError:
            print(f"❌ 数据库连接失败: 数据库 '{self.conn_params['database']}' 不存在")
            print("💡 解决方案: 请确保PostgreSQL已安装并创建了数据库")
            self.logger.error(f"数据库不存在: {self.conn_params['database']}")
            return False
            
        except asyncpg.exceptions.InvalidPasswordError:
            print(f"❌ 数据库连接失败: 用户名或密码错误")
            print("💡 解决方案: 请检查用户名和密码是否正确")
            self.logger.error("数据库认证失败")
            return False
            
        except asyncpg.exceptions.ConnectionDoesNotExistError:
            print(f"❌ 数据库连接失败: 无法连接到PostgreSQL服务器")
            print("💡 解决方案: 请检查PostgreSQL服务是否已启动")
            self.logger.error("无法连接到数据库服务器")
            return False
            
        except OSError as e:
            if "Connection refused" in str(e):
                print(f"❌ 数据库连接失败: 连接被拒绝 (端口 {self.conn_params['port']})")
                print("💡 解决方案:")
                print("   1. 检查PostgreSQL服务是否已启动")
                print("   2. 检查防火墙设置")
                print("   3. 验证端口号是否正确")
            elif "Name or service not known" in str(e):
                print(f"❌ 数据库连接失败: 主机名解析失败")
                print("💡 解决方案: 检查主机名是否正确")
            else:
                print(f"❌ 数据库连接失败: 网络错误 - {e}")
            self.logger.error(f"网络连接错误: {e}")
            return False
            
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            print("💡 请检查:")
            print("   1. PostgreSQL是否已安装")
            print("   2. PostgreSQL服务是否已启动")
            print("   3. 数据库连接参数是否正确")
            print("   4. 防火墙是否阻止了连接")
            self.logger.error(f"连接数据库失败: {e}")
            return False
    
    async def _init_tables(self):
        """初始化数据库表结构"""
        async with self.pool.acquire() as conn:
            try:
                # 创建白名单表
                await conn.execute('''
                CREATE TABLE IF NOT EXISTS whitelist (
                    id SERIAL PRIMARY KEY,
                    module TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    UNIQUE(module, name)
                )''')
                
                # 创建白名单历史表
                await conn.execute('''
                CREATE TABLE IF NOT EXISTS whitelist_history (
                    id SERIAL PRIMARY KEY,
                    module TEXT NOT NULL,
                    name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    old_data JSONB,
                    new_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT
                )''')
                
                # 创建索引
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_whitelist_module ON whitelist(module)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_whitelist_active ON whitelist(is_active)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_whitelist_name ON whitelist(name)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_whitelist_history_module ON whitelist_history(module)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_whitelist_history_created_at ON whitelist_history(created_at)')
                
                self.logger.info("数据库白名单表结构初始化成功")
                
            except Exception as e:
                self.logger.error(f"初始化数据库表结构失败: {e}")
                raise
    
    async def add_whitelist_item(self, module: str, name: str, description: str = None) -> bool:
        """
        添加白名单项
        
        Args:
            module: 模块名称
            name: 白名单名称
            description: 描述信息
            
        Returns:
            bool: 操作是否成功
        """
        if not self._validate_module(module):
            return False
            
        if not name or not name.strip():
            self.logger.error("白名单名称不能为空")
            return False
            
        name = name.strip()
        
        async with self.pool.acquire() as conn:
            try:
                # 检查是否已存在
                existing = await conn.fetchrow(
                    'SELECT id FROM whitelist WHERE module = $1 AND name = $2',
                    module, name
                )
                
                if existing:
                    self.logger.warning(f"白名单项已存在: {module} - {name}")
                    return False
                
                # 插入新记录
                await conn.execute('''
                INSERT INTO whitelist (module, name, description, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5)
                ''', module, name, description, datetime.now(), datetime.now())
                
                # 记录历史
                await self._record_history(conn, module, name, 'add', None, {
                    'name': name,
                    'description': description
                })
                
                self.logger.info(f"成功添加白名单项: {module} - {name}")
                return True
                
            except Exception as e:
                self.logger.error(f"添加白名单项失败: {e}")
                return False
    
    async def remove_whitelist_item(self, module: str, name: str) -> bool:
        """
        删除白名单项
        
        Args:
            module: 模块名称
            name: 白名单名称
            
        Returns:
            bool: 操作是否成功
        """
        if not self._validate_module(module):
            return False
            
        async with self.pool.acquire() as conn:
            try:
                # 获取旧数据
                old_data = await conn.fetchrow(
                    'SELECT * FROM whitelist WHERE module = $1 AND name = $2',
                    module, name
                )
                
                if not old_data:
                    self.logger.warning(f"白名单项不存在: {module} - {name}")
                    return False
                
                # 删除记录
                await conn.execute(
                    'DELETE FROM whitelist WHERE module = $1 AND name = $2',
                    module, name
                )
                
                # 记录历史
                await self._record_history(conn, module, name, 'remove', dict(old_data), None)
                
                self.logger.info(f"成功删除白名单项: {module} - {name}")
                return True
                
            except Exception as e:
                self.logger.error(f"删除白名单项失败: {e}")
                return False
    
    async def update_whitelist_item(self, module: str, old_name: str, new_name: str, description: str = None) -> bool:
        """
        更新白名单项
        
        Args:
            module: 模块名称
            old_name: 旧名称
            new_name: 新名称
            description: 描述信息
            
        Returns:
            bool: 操作是否成功
        """
        if not self._validate_module(module):
            return False
            
        if not new_name or not new_name.strip():
            self.logger.error("新名称不能为空")
            return False
            
        new_name = new_name.strip()
        
        async with self.pool.acquire() as conn:
            try:
                # 获取旧数据
                old_data = await conn.fetchrow(
                    'SELECT * FROM whitelist WHERE module = $1 AND name = $2',
                    module, old_name
                )
                
                if not old_data:
                    self.logger.warning(f"白名单项不存在: {module} - {old_name}")
                    return False
                
                # 如果名称有变化，检查新名称是否已存在
                if old_name != new_name:
                    existing = await conn.fetchrow(
                        'SELECT id FROM whitelist WHERE module = $1 AND name = $2',
                        module, new_name
                    )
                    
                    if existing:
                        self.logger.warning(f"新名称已存在: {module} - {new_name}")
                        return False
                
                # 更新记录
                await conn.execute('''
                UPDATE whitelist 
                SET name = $1, description = $2, updated_at = $3
                WHERE module = $4 AND name = $5
                ''', new_name, description, datetime.now(), module, old_name)
                
                # 记录历史
                await self._record_history(conn, module, new_name, 'update', dict(old_data), {
                    'name': new_name,
                    'description': description
                })
                
                self.logger.info(f"成功更新白名单项: {module} - {old_name} -> {new_name}")
                return True
                
            except Exception as e:
                self.logger.error(f"更新白名单项失败: {e}")
                return False
    
    async def get_whitelist(self, module: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        获取指定模块的白名单
        
        Args:
            module: 模块名称
            active_only: 是否只获取活跃的记录
            
        Returns:
            List[Dict]: 白名单列表
        """
        if not self._validate_module(module):
            return []
            
        async with self.pool.acquire() as conn:
            try:
                if active_only:
                    query = '''
                    SELECT id, module, name, description, created_at, updated_at, is_active
                    FROM whitelist 
                    WHERE module = $1 AND is_active = TRUE
                    ORDER BY name
                    '''
                    rows = await conn.fetch(query, module)
                else:
                    query = '''
                    SELECT id, module, name, description, created_at, updated_at, is_active
                    FROM whitelist 
                    WHERE module = $1
                    ORDER BY name
                    '''
                    rows = await conn.fetch(query, module)
                
                return [dict(row) for row in rows]
                
            except Exception as e:
                self.logger.error(f"获取白名单失败: {e}")
                return []
    
    async def get_whitelist_names(self, module: str) -> List[str]:
        """
        获取指定模块的白名单名称列表（只返回名称）
        
        Args:
            module: 模块名称
            
        Returns:
            List[str]: 白名单名称列表
        """
        if not self._validate_module(module):
            return []
        
        if not self.pool:
            self.logger.error("数据库连接池未初始化，请先调用connect()方法")
            return []
        
        try:
            # 🔧 防死锁：为读取操作添加超时保护，避免在写入时被阻塞
            conn = await asyncio.wait_for(self.pool.acquire(), timeout=10.0)
            try:
                # 🔧 防死锁：使用快速只读查询，设置较短超时
                rows = await asyncio.wait_for(
                    conn.fetch('''
                    SELECT name FROM whitelist 
                    WHERE module = $1 AND is_active = TRUE
                    ORDER BY name
                    ''', module),
                    timeout=8.0
                )
                
                result = [row['name'] for row in rows]
                self.logger.debug(f"🔍 [并发控制] 读取白名单成功: {module}, {len(result)} 个项目")
                return result
            finally:
                # 释放数据库连接
                await self.pool.release(conn)
                
        except asyncio.TimeoutError:
            # 🔧 防死锁：读取超时时返回空列表，避免阻塞主程序
            self.logger.warning(f"⏰ [并发控制] 读取白名单超时: {module}, 可能正在进行写入操作")
            return []
        except Exception as e:
            self.logger.error(f"❌ [并发控制] 获取白名单名称列表失败: {e}")
            return []
    
    async def batch_add_whitelist(self, module: str, names: List[str], description: str = None) -> Dict[str, Any]:
        """
        批量添加白名单项
        
        Args:
            module: 模块名称
            names: 白名单名称列表
            description: 描述信息
            
        Returns:
            Dict: 操作结果统计
        """
        if not self._validate_module(module):
            return {'success': False, 'message': '无效的模块名称'}
            
        if not names:
            return {'success': False, 'message': '名称列表不能为空'}
        
        result = {
            'success': True,
            'total': len(names),
            'added': 0,
            'skipped': 0,
            'failed': 0,
            'details': []
        }
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for name in names:
                    if not name or not name.strip():
                        result['skipped'] += 1
                        result['details'].append(f"跳过空名称")
                        continue
                    
                    name = name.strip()
                    
                    try:
                        # 检查是否已存在
                        existing = await conn.fetchrow(
                            'SELECT id FROM whitelist WHERE module = $1 AND name = $2',
                            module, name
                        )
                        
                        if existing:
                            result['skipped'] += 1
                            result['details'].append(f"跳过已存在项目: {name}")
                            continue
                        
                        # 插入新记录
                        await conn.execute('''
                        INSERT INTO whitelist (module, name, description, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5)
                        ''', module, name, description, datetime.now(), datetime.now())
                        
                        # 记录历史
                        await self._record_history(conn, module, name, 'batch_add', None, {
                            'name': name,
                            'description': description
                        })
                        
                        result['added'] += 1
                        result['details'].append(f"成功添加: {name}")
                        
                    except Exception as e:
                        result['failed'] += 1
                        result['details'].append(f"添加失败 {name}: {str(e)}")
                        self.logger.error(f"批量添加白名单项失败: {name} - {e}")
        
        self.logger.info(f"批量添加白名单完成: {module} - 添加{result['added']}个，跳过{result['skipped']}个，失败{result['failed']}个")
        return result
    
    async def batch_remove_whitelist(self, module: str, names: List[str]) -> Dict[str, Any]:
        """
        批量删除白名单项
        
        Args:
            module: 模块名称
            names: 白名单名称列表
            
        Returns:
            Dict: 操作结果统计
        """
        if not self._validate_module(module):
            return {'success': False, 'message': '无效的模块名称'}
            
        if not names:
            return {'success': False, 'message': '名称列表不能为空'}
        
        result = {
            'success': True,
            'total': len(names),
            'removed': 0,
            'not_found': 0,
            'failed': 0,
            'details': []
        }
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for name in names:
                    if not name or not name.strip():
                        result['not_found'] += 1
                        result['details'].append(f"跳过空名称")
                        continue
                    
                    name = name.strip()
                    
                    try:
                        # 获取旧数据
                        old_data = await conn.fetchrow(
                            'SELECT * FROM whitelist WHERE module = $1 AND name = $2',
                            module, name
                        )
                        
                        if not old_data:
                            result['not_found'] += 1
                            result['details'].append(f"未找到项目: {name}")
                            continue
                        
                        # 删除记录
                        await conn.execute(
                            'DELETE FROM whitelist WHERE module = $1 AND name = $2',
                            module, name
                        )
                        
                        # 记录历史
                        await self._record_history(conn, module, name, 'batch_remove', dict(old_data), None)
                        
                        result['removed'] += 1
                        result['details'].append(f"成功删除: {name}")
                        
                    except Exception as e:
                        result['failed'] += 1
                        result['details'].append(f"删除失败 {name}: {str(e)}")
                        self.logger.error(f"批量删除白名单项失败: {name} - {e}")
        
        self.logger.info(f"批量删除白名单完成: {module} - 删除{result['removed']}个，未找到{result['not_found']}个，失败{result['failed']}个")
        return result
    
    async def replace_whitelist(self, module: str, names: List[str], description: str = None) -> Dict[str, Any]:
        """
        替换指定模块的整个白名单
        
        Args:
            module: 模块名称
            names: 新的白名单名称列表
            description: 描述信息
            
        Returns:
            Dict: 操作结果统计
        """
        if not self._validate_module(module):
            return {'success': False, 'message': '无效的模块名称'}
        
        if not self._check_connection():
            return {'success': False, 'message': '数据库连接未初始化'}
        
        # 🔧 防死锁：使用操作锁防止并发写入冲突
        async with self._operation_lock:
            try:
                # 记录操作开始时间
                operation_start = time.time()
                self._last_operation_time[module] = operation_start
                
                self.logger.info(f"🔐 [并发控制] 获取写入锁: {module}")
                
                # 🔧 防死锁：使用较短的连接超时，避免长时间占用连接
                conn = await asyncio.wait_for(self.pool.acquire(), timeout=15.0)
                try:
                    # 🔧 防死锁：使用READ COMMITTED隔离级别，允许并发读取
                    async with conn.transaction(isolation='read_committed'):
                        try:
                            # 获取现有白名单
                            existing_names = await asyncio.wait_for(
                                conn.fetch('SELECT name FROM whitelist WHERE module = $1', module),
                                timeout=10.0
                            )
                            existing_names = [row['name'] for row in existing_names]
                            
                            # 清除现有白名单
                            await asyncio.wait_for(
                                conn.execute('DELETE FROM whitelist WHERE module = $1', module),
                                timeout=10.0
                            )
                            
                            # 记录清除历史
                            await self._record_history(conn, module, 'ALL', 'replace_clear', {
                                'old_names': existing_names
                            }, None)
                            
                            # 批量添加新白名单
                            added_count = 0
                            failed_count = 0
                            details = []
                            
                            # 🔧 优化：使用批量插入提高性能，减少事务时间
                            if names:
                                # 准备批量插入数据
                                insert_data = []
                                for name in names:
                                    if name and name.strip():
                                        insert_data.append((
                                            module, 
                                            name.strip(), 
                                            description, 
                                            datetime.now(), 
                                            datetime.now()
                                        ))
                                
                                if insert_data:
                                    try:
                                        # 使用executemany进行批量插入
                                        await asyncio.wait_for(
                                            conn.executemany('''
                                            INSERT INTO whitelist (module, name, description, created_at, updated_at)
                                            VALUES ($1, $2, $3, $4, $5)
                                            ''', insert_data),
                                            timeout=20.0
                                        )
                                        added_count = len(insert_data)
                                        details = [f"批量添加 {added_count} 个项目"]
                                        
                                    except Exception as e:
                                        self.logger.error(f"批量插入失败，回退到逐个插入: {e}")
                                        # 回退到原有的逐个插入方式
                                        for name in names:
                                            if not name or not name.strip():
                                                continue
                                            
                                            name = name.strip()
                                            
                                            try:
                                                await conn.execute('''
                                                INSERT INTO whitelist (module, name, description, created_at, updated_at)
                                                VALUES ($1, $2, $3, $4, $5)
                                                ''', module, name, description, datetime.now(), datetime.now())
                                                
                                                added_count += 1
                                                details.append(f"成功添加: {name}")
                                                
                                            except Exception as e:
                                                failed_count += 1
                                                details.append(f"添加失败 {name}: {str(e)}")
                                                self.logger.error(f"替换白名单时添加项目失败: {name} - {e}")
                            
                            # 记录替换历史
                            await self._record_history(conn, module, 'ALL', 'replace_add', None, {
                                'new_names': names,
                                'added_count': added_count,
                                'failed_count': failed_count
                            })
                            
                            operation_duration = time.time() - operation_start
                            
                            result = {
                                'success': True,
                                'old_count': len(existing_names),
                                'new_count': len(names),
                                'added': added_count,
                                'failed': failed_count,
                                'details': details,
                                'duration': round(operation_duration, 2)
                            }
                            
                            self.logger.info(f"✅ [并发控制] 替换白名单完成: {module} - 原有{result['old_count']}个，新增{result['added']}个，失败{result['failed']}个，耗时{result['duration']}秒")
                            return result
                            
                        except asyncio.TimeoutError:
                            error_msg = "数据库操作超时，可能存在死锁"
                            self.logger.error(f"❌ [并发控制] {error_msg}: {module}")
                            return {'success': False, 'message': error_msg}
                        except Exception as e:
                            self.logger.error(f"❌ [并发控制] 替换白名单失败: {e}")
                            return {'success': False, 'message': str(e)}
                finally:
                    # 释放数据库连接
                    await self.pool.release(conn)
                            
            except asyncio.TimeoutError:
                error_msg = "获取数据库连接超时，连接池可能已满"
                self.logger.error(f"❌ [并发控制] {error_msg}: {module}")
                return {'success': False, 'message': error_msg}
            except Exception as e:
                self.logger.error(f"❌ [并发控制] 操作失败: {e}")
                return {'success': False, 'message': str(e)}
            finally:
                self.logger.info(f"🔓 [并发控制] 释放写入锁: {module}")
    
    async def get_whitelist_history(self, module: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取白名单历史记录
        
        Args:
            module: 模块名称
            limit: 返回记录数量限制
            
        Returns:
            List[Dict]: 历史记录列表
        """
        if not self._validate_module(module):
            return []
            
        async with self.pool.acquire() as conn:
            try:
                rows = await conn.fetch('''
                SELECT id, module, name, action, old_data, new_data, created_at, created_by
                FROM whitelist_history 
                WHERE module = $1
                ORDER BY created_at DESC
                LIMIT $2
                ''', module, limit)
                
                return [dict(row) for row in rows]
                
            except Exception as e:
                self.logger.error(f"获取白名单历史记录失败: {e}")
                return []
    
    async def get_all_modules_whitelist(self) -> Dict[str, List[str]]:
        """
        获取所有模块的白名单
        
        Returns:
            Dict[str, List[str]]: 模块名称到白名单的映射
        """
        result = {}
        
        async with self.pool.acquire() as conn:
            try:
                rows = await conn.fetch('''
                SELECT module, name FROM whitelist 
                WHERE is_active = TRUE
                ORDER BY module, name
                ''')
                
                for row in rows:
                    module = row['module']
                    name = row['name']
                    
                    if module not in result:
                        result[module] = []
                    
                    result[module].append(name)
                
                return result
                
            except Exception as e:
                self.logger.error(f"获取所有模块白名单失败: {e}")
                return {}
    
    async def search_whitelist(self, query: str, modules: List[str] = None) -> List[Dict[str, Any]]:
        """
        搜索白名单项
        
        Args:
            query: 搜索查询
            modules: 要搜索的模块列表，None表示搜索所有模块
            
        Returns:
            List[Dict]: 搜索结果列表
        """
        async with self.pool.acquire() as conn:
            try:
                if modules:
                    # 验证模块名称
                    modules = [m for m in modules if self._validate_module(m, raise_error=False)]
                    if not modules:
                        return []
                    
                    # 构建模块条件
                    module_placeholders = ', '.join(['$' + str(i+2) for i in range(len(modules))])
                    sql = f'''
                    SELECT id, module, name, description, created_at, updated_at, is_active
                    FROM whitelist 
                    WHERE name ILIKE $1 AND module IN ({module_placeholders}) AND is_active = TRUE
                    ORDER BY module, name
                    '''
                    rows = await conn.fetch(sql, f'%{query}%', *modules)
                else:
                    rows = await conn.fetch('''
                    SELECT id, module, name, description, created_at, updated_at, is_active
                    FROM whitelist 
                    WHERE name ILIKE $1 AND is_active = TRUE
                    ORDER BY module, name
                    ''', f'%{query}%')
                
                return [dict(row) for row in rows]
                
            except Exception as e:
                self.logger.error(f"搜索白名单失败: {e}")
                return []
    
    async def get_whitelist_stats(self) -> Dict[str, Any]:
        """
        获取白名单统计信息
        
        Returns:
            Dict: 统计信息
        """
        async with self.pool.acquire() as conn:
            try:
                # 总体统计
                total_active = await conn.fetchval(
                    'SELECT COUNT(*) FROM whitelist WHERE is_active = TRUE'
                )
                total_inactive = await conn.fetchval(
                    'SELECT COUNT(*) FROM whitelist WHERE is_active = FALSE'
                )
                
                # 按模块统计
                module_stats = await conn.fetch('''
                SELECT module, COUNT(*) as count
                FROM whitelist 
                WHERE is_active = TRUE
                GROUP BY module
                ORDER BY module
                ''')
                
                # 最近活动统计
                recent_history = await conn.fetchval('''
                SELECT COUNT(*) FROM whitelist_history
                WHERE created_at > NOW() - INTERVAL '7 days'
                ''')
                
                return {
                    'total_active': total_active,
                    'total_inactive': total_inactive,
                    'total': total_active + total_inactive,
                    'modules': {row['module']: row['count'] for row in module_stats},
                    'recent_changes': recent_history,
                    'supported_modules': self.supported_modules
                }
                
            except Exception as e:
                self.logger.error(f"获取白名单统计信息失败: {e}")
                return {}
    
    async def _record_history(self, conn, module: str, name: str, action: str, 
                            old_data: Dict = None, new_data: Dict = None, created_by: str = None):
        """记录历史操作"""
        try:
            await conn.execute('''
            INSERT INTO whitelist_history (module, name, action, old_data, new_data, created_at, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', module, name, action, 
                json.dumps(old_data) if old_data else None,
                json.dumps(new_data) if new_data else None,
                datetime.now(), created_by)
        except Exception as e:
            self.logger.error(f"记录历史操作失败: {e}")
    
    def _validate_module(self, module: str, raise_error: bool = True) -> bool:
        """验证模块名称"""
        if module not in self.supported_modules:
            if raise_error:
                self.logger.error(f"不支持的模块: {module}，支持的模块: {list(self.supported_modules.keys())}")
            return False
        return True
    
    def _check_connection(self) -> bool:
        """检查数据库连接是否可用"""
        if not self.pool:
            self.logger.error("数据库连接池未初始化，请先调用connect()方法")
            print("❌ 数据库连接池未初始化")
            print("💡 请先确保数据库连接成功")
            return False
        return True
    
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
    """示例用法"""
    # 创建白名单管理工具实例
    whitelist_tool = WhitelistDBTool()
    
    try:
        # 连接数据库
        await whitelist_tool.connect()
        
        # 添加白名单项
        await whitelist_tool.add_whitelist_item('larkbusiness', '测试用户1', '测试描述')
        
        # 批量添加白名单项
        names = ['测试用户2', '测试用户3', '测试用户4']
        result = await whitelist_tool.batch_add_whitelist('larkbusiness', names)
        print(f"批量添加结果: {result}")
        
        # 获取白名单
        whitelist = await whitelist_tool.get_whitelist('larkbusiness')
        print(f"larkbusiness 白名单: {whitelist}")
        
        # 获取白名单名称列表
        names = await whitelist_tool.get_whitelist_names('larkbusiness')
        print(f"larkbusiness 白名单名称: {names}")
        
        # 搜索白名单
        search_results = await whitelist_tool.search_whitelist('测试')
        print(f"搜索结果: {search_results}")
        
        # 获取统计信息
        stats = await whitelist_tool.get_whitelist_stats()
        print(f"统计信息: {stats}")
        
        # 获取历史记录
        history = await whitelist_tool.get_whitelist_history('larkbusiness')
        print(f"历史记录: {history}")
        
    finally:
        # 关闭连接
        await whitelist_tool.close()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage()) 