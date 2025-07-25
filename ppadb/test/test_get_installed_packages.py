#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试获取已安装应用列表功能
"""

import os
import sys
import pathlib
import json

# 将项目根目录添加到Python路径
current_dir = pathlib.Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# 导入PPADB工具
from ...ppadb.ppadbtool import PPADBTool


def test_get_installed_packages():
    """测试获取已安装应用列表功能"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 检查设备连接
    if not adb_tool.is_device_connected():
        print("未连接设备，无法进行测试")
        return
    
    # 获取所有应用
    print("\n===== 获取所有应用 =====")
    all_packages = adb_tool.get_installed_packages()
    print(f"获取结果: {all_packages['message']}")
    
    # 获取系统应用
    print("\n===== 获取系统应用 =====")
    system_packages = adb_tool.get_installed_packages(filter_type="system")
    print(f"获取结果: {system_packages['message']}")
    
    # 获取第三方应用
    print("\n===== 获取第三方应用 =====")
    third_party_packages = adb_tool.get_installed_packages(filter_type="3rd")
    print(f"获取结果: {third_party_packages['message']}")
    
    # 保存结果到文件
    if all_packages['success']:
        output_file = current_dir / "all_packages.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_packages, f, ensure_ascii=False, indent=2)
        print(f"\n所有应用列表已保存到: {output_file}")
    
    if system_packages['success']:
        output_file = current_dir / "system_packages.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(system_packages, f, ensure_ascii=False, indent=2)
        print(f"系统应用列表已保存到: {output_file}")
    
    if third_party_packages['success']:
        output_file = current_dir / "third_party_packages.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(third_party_packages, f, ensure_ascii=False, indent=2)
        print(f"第三方应用列表已保存到: {output_file}")
    
    # 打印部分应用信息
    if all_packages['success'] and all_packages['packages']:
        print("\n===== 应用列表示例（前10个） =====")
        for i, package in enumerate(all_packages['packages'][:10], 1):
            print(f"{i}. {package['package_name']} - {'系统应用' if package['system'] else '第三方应用'}")
            print(f"   路径: {package['path']}")


def main():
    """主函数"""
    test_get_installed_packages()


if __name__ == "__main__":
    main() 