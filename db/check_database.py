#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库状态检查脚本

用于诊断PostgreSQL连接问题，提供详细的检查结果和解决方案。
"""

import asyncio
import asyncpg
import platform
import subprocess
import sys
import socket
from pathlib import Path


async def check_database_connection():
    """检查数据库连接状态"""
    print("🔍 PostgreSQL 数据库连接检查")
    print("=" * 50)
    
    # 数据库连接参数
    conn_params = {
        'user': 'postgres',
        'password': 'YOUR_DATABASE_PASSWORD_HERE',
        'database': 'YOUR_DATABASE_NAME_HERE',
        'host': 'localhost',
        'port': 5432
    }
    
    print(f"📋 连接参数:")
    print(f"   主机: {conn_params['host']}")
    print(f"   端口: {conn_params['port']}")
    print(f"   用户: {conn_params['user']}")
    print(f"   数据库: {conn_params['database']}")
    print()
    
    # 1. 检查端口是否开放
    print("1️⃣ 检查端口连通性...")
    port_open = check_port_open(conn_params['host'], conn_params['port'])
    if port_open:
        print(f"   ✅ 端口 {conn_params['port']} 可访问")
    else:
        print(f"   ❌ 端口 {conn_params['port']} 不可访问")
        print("   💡 可能原因:")
        print("      - PostgreSQL 服务未启动")
        print("      - 防火墙阻止连接")
        print("      - PostgreSQL 配置错误")
        return False
    
    # 2. 尝试数据库连接
    print("\n2️⃣ 尝试数据库连接...")
    try:
        conn = await asyncpg.connect(**conn_params)
        
        # 获取数据库版本信息
        version = await conn.fetchval('SELECT version()')
        print(f"   ✅ 数据库连接成功！")
        print(f"   📦 PostgreSQL 版本: {version}")
        
        # 检查数据库权限
        databases = await conn.fetch("SELECT datname FROM pg_database WHERE datistemplate = false")
        print(f"   📊 可访问的数据库: {[db['datname'] for db in databases]}")
        
        await conn.close()
        return True
        
    except asyncpg.exceptions.InvalidPasswordError:
        print(f"   ❌ 认证失败：用户名或密码错误")
        print("   💡 解决方案:")
        print("      - 检查用户名和密码是否正确")
        print("      - 确认用户存在且有相应权限")
        return False
        
    except asyncpg.exceptions.InvalidCatalogNameError:
        print(f"   ❌ 数据库 '{conn_params['database']}' 不存在")
        print("   💡 解决方案:")
        print("      - 创建对应的数据库")
        print("      - 或修改连接参数使用已存在的数据库")
        return False
        
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        print("   💡 请检查数据库服务状态")
        return False


def check_port_open(host, port):
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_postgresql_windows():
    """检查Windows上的PostgreSQL服务状态"""
    if platform.system() != 'Windows':
        return
    
    print("\n3️⃣ Windows PostgreSQL 服务检查...")
    
    try:
        # 检查PostgreSQL服务
        result = subprocess.run(['sc', 'query', 'postgresql'], 
                              capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            if 'RUNNING' in result.stdout:
                print("   ✅ PostgreSQL 服务正在运行")
            elif 'STOPPED' in result.stdout:
                print("   ⚠️ PostgreSQL 服务已停止")
                print("   💡 启动服务: sc start postgresql")
            else:
                print("   ⚠️ PostgreSQL 服务状态未知")
        else:
            print("   ❌ 未找到 PostgreSQL 服务")
            print("   💡 可能需要安装 PostgreSQL")
            
    except Exception as e:
        print(f"   ❌ 检查服务状态失败: {e}")


def check_postgresql_installation():
    """检查PostgreSQL是否已安装"""
    print("\n4️⃣ 检查 PostgreSQL 安装...")
    
    # 检查 psql 命令是否可用
    try:
        result = subprocess.run(['psql', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ PostgreSQL 客户端已安装: {result.stdout.strip()}")
        else:
            print("   ❌ PostgreSQL 客户端未安装")
    except FileNotFoundError:
        print("   ❌ PostgreSQL 客户端未安装")
        print("   💡 安装方法:")
        print("      - 官方下载: https://www.postgresql.org/download/")
        print("      - Chocolatey: choco install postgresql")
        print("      - Winget: winget install PostgreSQL.PostgreSQL")


async def test_whitelist_operations():
    """测试白名单功能"""
    print("\n5️⃣ 测试白名单功能...")
    
    try:
        # 导入白名单工具
        sys.path.append(str(Path(__file__).parent))
        from whitelist_db_tool import WhitelistDBTool
        
        # 创建工具实例
        whitelist_tool = WhitelistDBTool()
        
        # 尝试连接
        connected = await whitelist_tool.connect()
        if not connected:
            print("   ❌ 白名单工具连接失败")
            return False
        
        try:
            # 测试获取白名单
            whitelist = await whitelist_tool.get_whitelist_names('larkbusiness')
            print(f"   ✅ 白名单功能正常，当前有 {len(whitelist)} 个条目")
            
            # 获取统计信息
            stats = await whitelist_tool.get_whitelist_stats()
            print(f"   📊 数据库统计: {stats}")
            
            return True
            
        finally:
            await whitelist_tool.close()
            
    except ImportError as e:
        print(f"   ❌ 导入白名单工具失败: {e}")
        return False
    except Exception as e:
        print(f"   ❌ 测试白名单功能失败: {e}")
        return False


async def main():
    """主函数"""
    print("🚀 AutoOOIN 数据库状态检查器")
    print(f"🖥️ 操作系统: {platform.system()} {platform.release()}")
    print()
    
    # 检查数据库连接
    db_ok = await check_database_connection()
    
    # 如果是Windows，检查服务状态
    if platform.system() == 'Windows':
        check_postgresql_windows()
    
    # 检查安装状态
    check_postgresql_installation()
    
    # 如果数据库连接正常，测试白名单功能
    if db_ok:
        await test_whitelist_operations()
    
    print("\n" + "=" * 50)
    
    if db_ok:
        print("🎉 数据库检查完成！一切正常。")
    else:
        print("⚠️ 数据库连接有问题，请根据上述提示进行修复。")
        print("\n📋 常见解决方案:")
        print("1. 安装 PostgreSQL")
        print("2. 启动 PostgreSQL 服务")
        print("3. 检查防火墙设置")
        print("4. 确认数据库用户和密码")


if __name__ == "__main__":
    asyncio.run(main()) 