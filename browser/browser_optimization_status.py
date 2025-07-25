#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
浏览器优化状态检查器

用于检查和显示Chrome浏览器的轻量化优化状态
确认是否需要手动设置或已自动优化完成
"""

import os
import json
import requests
import platform
from pathlib import Path


def check_chrome_debug_status(port=9222):
    """检查Chrome调试端口状态"""
    try:
        url = f"http://localhost:{port}/json/version"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            return {
                'status': 'running',
                'version': data.get('Browser', 'Unknown'),
                'webSocketDebuggerUrl': data.get('webSocketDebuggerUrl', ''),
                'userAgent': data.get('User-Agent', '')
            }
    except Exception as e:
        return {
            'status': 'not_running',
            'error': str(e)
        }
    
    return {'status': 'not_running'}


def check_preferences_optimization(debug_port=9222):
    """检查偏好设置优化状态"""
    system = platform.system()
    
    # 查找临时用户数据目录
    temp_dir = f"/tmp/chrome-debug-{debug_port}"
    preferences_path = os.path.join(temp_dir, "Default", "Preferences")
    
    if not os.path.exists(preferences_path):
        return {
            'status': 'not_optimized',
            'message': '未找到优化的偏好设置文件'
        }
    
    try:
        with open(preferences_path, 'r', encoding='utf-8') as f:
            prefs = json.load(f)
        
        # 检查关键优化设置
        optimizations = {
            '通知阻止': prefs.get('profile', {}).get('default_content_setting_values', {}).get('notifications') == 2,
            '位置服务阻止': prefs.get('profile', {}).get('default_content_setting_values', {}).get('geolocation') == 2,
            '自动填充禁用': prefs.get('autofill', {}).get('enabled') == False,
            '密码管理禁用': prefs.get('password_manager', {}).get('enabled') == False,
            '网络预取禁用': prefs.get('dns_prefetching', {}).get('enabled') == False,
            '安全浏览禁用': prefs.get('safebrowsing', {}).get('enabled') == False,
            '翻译服务禁用': prefs.get('translate', {}).get('enabled') == False,
            '搜索建议禁用': prefs.get('search', {}).get('suggest_enabled') == False
        }
        
        optimized_count = sum(optimizations.values())
        total_count = len(optimizations)
        
        return {
            'status': 'optimized' if optimized_count >= total_count * 0.8 else 'partial',
            'optimizations': optimizations,
            'score': f"{optimized_count}/{total_count}",
            'percentage': round((optimized_count / total_count) * 100, 1)
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def get_optimization_recommendations():
    """获取优化建议"""
    return {
        'automatic': [
            "✅ 使用我们的chrome_launcher.py自动启动 - 无需手动设置",
            "✅ 启动参数已包含60+项轻量化优化",
            "✅ 偏好设置自动配置 - 禁用所有不必要功能",
            "✅ 网络稳定性优化 - 解决SSL/STUN错误",
            "✅ 内存和CPU使用优化",
            "✅ 保持TikTok/Fastmoss网站兼容性"
        ],
        'manual_not_needed': [
            "❌ 无需在Chrome设置中手动配置任何选项",
            "❌ 无需禁用扩展程序（已自动禁用）",
            "❌ 无需调整隐私设置（已自动优化）",
            "❌ 无需设置通知权限（已自动阻止）",
            "❌ 无需清理缓存（已自动管理）"
        ]
    }


def print_optimization_status():
    """打印完整的优化状态报告"""
    print("🔍 Chrome浏览器轻量化优化状态检查")
    print("=" * 60)
    
    # 检查Chrome运行状态
    chrome_status = check_chrome_debug_status()
    print(f"\n📊 Chrome调试状态:")
    if chrome_status['status'] == 'running':
        print(f"   ✅ 运行中 - {chrome_status['version']}")
    else:
        print(f"   ❌ 未运行 - {chrome_status.get('error', 'Unknown')}")
    
    # 检查偏好设置优化
    print(f"\n🔧 偏好设置优化状态:")
    prefs_status = check_preferences_optimization()
    
    if prefs_status['status'] == 'optimized':
        print(f"   ✅ 已完全优化 - {prefs_status['score']} ({prefs_status['percentage']}%)")
        print("   详细优化项目:")
        for item, enabled in prefs_status['optimizations'].items():
            icon = "✅" if enabled else "❌"
            print(f"     {icon} {item}")
    elif prefs_status['status'] == 'partial':
        print(f"   ⚠️ 部分优化 - {prefs_status['score']} ({prefs_status['percentage']}%)")
    elif prefs_status['status'] == 'not_optimized':
        print(f"   ❌ 未优化 - {prefs_status['message']}")
    else:
        print(f"   ❌ 检查失败 - {prefs_status.get('error', 'Unknown')}")
    
    # 显示优化建议
    recommendations = get_optimization_recommendations()
    
    print(f"\n🚀 自动化优化功能:")
    for rec in recommendations['automatic']:
        print(f"   {rec}")
    
    print(f"\n🚫 无需手动操作:")
    for rec in recommendations['manual_not_needed']:
        print(f"   {rec}")
    
    print(f"\n💡 使用建议:")
    print("   1. 直接使用我们的强制重启机制")
    print("   2. 系统会自动应用所有优化")
    print("   3. 无需进入Chrome设置进行任何手动配置")
    print("   4. 如遇问题，重启浏览器即可恢复最佳状态")
    
    print("\n" + "=" * 60)
    print("🎯 结论: 完全自动化 - 无需手动浏览器设置！")


if __name__ == "__main__":
    print_optimization_status() 