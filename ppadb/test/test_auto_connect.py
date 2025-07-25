#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试自动连接第一个设备功能
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


def test_auto_connect():
    """测试自动连接第一个设备功能"""
    print("\n===== 测试自动连接第一个设备 =====")
    
    # 初始化工具，不指定设备序列号，将自动连接第一个设备
    adb_tool = PPADBTool()
    
    # 检查是否已连接设备
    if adb_tool.is_device_connected():
        print("成功自动连接到第一个设备")
        
        # 获取当前设备详情
        current_device = adb_tool.get_current_device()
        
        if current_device['success']:
            device_info = current_device['device']
            
            print("\n===== 自动连接的设备 =====")
            print(f"序列号: {device_info['serial']}")
            print(f"状态: {device_info['state']}")
            
            if device_info['properties']:
                print("设备属性:")
                for key, value in device_info['properties'].items():
                    print(f"  {key}: {value}")
            
            # 保存设备信息到文件
            output_file = current_dir / "auto_connected_device.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(current_device, f, ensure_ascii=False, indent=2)
            print(f"\n设备信息已保存到: {output_file}")
        else:
            print(f"获取设备详情失败: {current_device['message']}")
    else:
        print("未能自动连接到设备，可能没有可用设备")


def main():
    """主函数"""
    test_auto_connect()


if __name__ == "__main__":
    main() 