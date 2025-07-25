#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试启动应用功能
"""

import os
import sys
import pathlib
import json
import time

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def test_launch_app():
    """测试启动应用功能"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法进行测试")
        return
    
    # 获取第三方应用列表
    packages_result = adb_tool.get_installed_packages(filter_type="3rd")
    if not packages_result['success'] or not packages_result['packages']:
        print("获取应用列表失败或没有第三方应用")
        
        # 尝试获取系统应用
        packages_result = adb_tool.get_installed_packages(filter_type="system")
        if not packages_result['success'] or not packages_result['packages']:
            print("获取系统应用列表也失败，无法继续测试")
            return
    
    # 显示可选应用列表
    print("\n===== 可选应用列表 =====")
    options = []
    
    # 添加常用系统应用
    common_apps = [
        {"package_name": "com.android.settings", "app_name": "设置"},
        {"package_name": "com.android.browser", "app_name": "浏览器"},
        {"package_name": "com.android.calculator2", "app_name": "计算器"},
    ]
    
    # 先添加常用应用
    for app in common_apps:
        options.append(app)
    
    # 再添加设备上的应用
    for package in packages_result['packages']:
        # 避免重复添加
        if not any(opt['package_name'] == package['package_name'] for opt in options):
            options.append(package)
    
    # 显示选项列表（限制数量）
    max_display = min(20, len(options))
    for i, app in enumerate(options[:max_display], 1):
        print(f"{i}. {app['package_name']} - {app['app_name']}")
    
    # 用户选择或输入应用包名
    print("\n请选择要启动的应用编号，或直接输入应用包名:")
    user_input = input("请输入 (1-{} 或应用包名): ".format(max_display))
    
    # 确定要启动的应用包名
    package_name = ""
    if user_input.isdigit():
        choice = int(user_input)
        if 1 <= choice <= max_display:
            package_name = options[choice - 1]['package_name']
        else:
            print("无效的选择")
            return
    else:
        # 用户输入的是包名
        package_name = user_input.strip()
    
    # 启动应用
    print(f"\n正在启动应用: {package_name}")
    result = adb_tool.launch_app(package_name)
    
    # 保存启动结果
    output_file = current_dir / "launch_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 显示结果
    print(f"启动结果: {result['message']}")
    if result['success']:
        print("应用启动成功!")
    else:
        print("启动失败，详细输出:")
        print(result['output'])
        
    print(f"\n启动结果已保存到: {output_file}")


def main():
    """主函数"""
    test_launch_app()


if __name__ == "__main__":
    main() 