#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库完全清空工具
完全清空PostgreSQL数据库中所有内容：
- 动态查询并删除数据库中的所有表（不管是什么表）
- 包括表结构、数据、索引、约束等

⚠️  注意：此工具会删除数据库中的所有表，程序下次运行时会自动重建需要的表
"""

import asyncio
import os
import sys
import asyncpg

# 添加项目根目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from .db.postgrestool import PostgresTool
from .cache.postgrescachetool import PostgresCacheTool


async def drop_all_tables_completely():
    """动态查询并删除数据库中的所有表"""
    
    print("准备完全清空PostgreSQL数据库中的所有表...")
    print("⚠️  注意：这会删除数据库中的所有表，不管是什么表！")
    
    # 数据库连接参数 - 使用默认值
    db_params = {
        'user': 'YOUR_DATABASE_USER_HERE',
        'password': 'YOUR_DATABASE_PASSWORD_HERE',
        'database': 'YOUR_DATABASE_NAME_HERE',
        'host': 'YOUR_DATABASE_HOST_HERE',
        'port': 5432  # Change to YOUR_DATABASE_PORT_HERE
    }
    
    try:
        # 直接建立数据库连接
        conn = await asyncpg.connect(**db_params)
        
        print("\n🔍 正在查询数据库中的所有表...")
        
        # 查询所有用户表（排除系统表）
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        if not tables:
            print("✅ 数据库中没有找到任何表，已经是空的！")
            return
        
        table_names = [row['tablename'] for row in tables]
        print(f"📋 找到 {len(table_names)} 个表：")
        for i, table_name in enumerate(table_names, 1):
            print(f"   {i}. {table_name}")
        
        print(f"\n🗑️  开始删除所有表...")
        
        # 使用事务确保原子操作
        async with conn.transaction():
            deleted_count = 0
            for table_name in table_names:
                try:
                    # 使用 CASCADE 删除表及其所有依赖
                    await conn.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                    print(f"  ✅ 已删除表: {table_name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ❌ 删除表 {table_name} 失败: {e}")
        
        print(f"\n🎉 数据库清理完成！")
        print(f"   - 总共找到: {len(table_names)} 个表")
        print(f"   - 成功删除: {deleted_count} 个表")
        print(f"   - 失败数量: {len(table_names) - deleted_count} 个表")
        
        # 验证删除结果
        remaining_tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        
        if remaining_tables:
            print(f"\n⚠️  仍有 {len(remaining_tables)} 个表未删除：")
            for row in remaining_tables:
                print(f"   - {row['tablename']}")
        else:
            print(f"\n✨ 数据库已完全清空，所有表都已删除！")
        
        print("💡 程序下次运行时会自动重建需要的表结构。")
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")
    finally:
        if 'conn' in locals():
            await conn.close()


def main():
    """主函数"""
    # 直接执行全删操作
    asyncio.run(drop_all_tables_completely())


if __name__ == "__main__":
    main() 