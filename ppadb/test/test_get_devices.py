#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试获取设备列表功能
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


def test_get_devices():
    """测试获取设备列表功能"""
    # 初始化工具
    adb_tool = PPADBTool()
    
    # 获取设备列表
    result = adb_tool.get_devices()
    
    # 打印结果
    print("\n===== 设备列表 =====")
    print(f"状态: {'成功' if result['success'] else '失败'}")
    print(f"消息: {result['message']}")
    
    if result['success'] and result['devices']:
        print(f"\n发现 {len(result['devices'])} 个设备:")
        
        for i, device in enumerate(result['devices'], 1):
            print(f"\n设备 {i}:")
            print(f"  序列号: {device['serial']}")
            print(f"  状态: {device['state']}")
            
            if device['properties']:
                print("  设备属性:")
                for key, value in device['properties'].items():
                    print(f"    {key}: {value}")
    else:
        print("未找到连接的设备")
    
    # 以JSON格式保存结果到文件
    output_file = current_dir / "devices_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_file}")


def main():
    """主函数"""
    test_get_devices()


if __name__ == "__main__":
    main() 