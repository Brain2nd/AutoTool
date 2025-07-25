#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试选择设备功能
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


def test_select_device():
    """测试选择设备功能"""
    # 初始化工具，不自动连接设备
    adb_tool = PPADBTool()
    
    # 获取设备列表
    devices_result = adb_tool.get_devices()
    
    if not devices_result['success'] or not devices_result['devices']:
        print("未找到可用设备，无法进行选择设备测试")
        return
    
    # 显示可用设备列表
    print("\n===== 可用设备列表 =====")
    for i, device in enumerate(devices_result['devices'], 1):
        print(f"{i}. {device['serial']} - {device['properties'].get('model', 'Unknown')}")
    
    # 请求用户选择设备
    try:
        choice = int(input("\n请选择设备编号 [1-{}]: ".format(len(devices_result['devices']))))
        if choice < 1 or choice > len(devices_result['devices']):
            print("无效的选择，将使用第一个设备")
            choice = 1
    except ValueError:
        print("无效的输入，将使用第一个设备")
        choice = 1
    
    # 获取选择的设备序列号
    selected_serial = devices_result['devices'][choice-1]['serial']
    
    # 尝试连接设备
    print(f"\n正在连接设备: {selected_serial}")
    success = adb_tool.select_device(selected_serial)
    
    if success:
        print("设备连接成功\n")
        
        # 获取当前设备详情
        current_device = adb_tool.get_current_device()
        
        if current_device['success']:
            device_info = current_device['device']
            
            print("===== 当前连接的设备 =====")
            print(f"序列号: {device_info['serial']}")
            print(f"状态: {device_info['state']}")
            
            if device_info['properties']:
                print("设备属性:")
                for key, value in device_info['properties'].items():
                    print(f"  {key}: {value}")
            
            # 保存设备信息到文件
            output_file = current_dir / "current_device.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(current_device, f, ensure_ascii=False, indent=2)
            print(f"\n设备信息已保存到: {output_file}")
            
            # 测试断开连接
            print("\n正在断开设备连接...")
            disconnect_result = adb_tool.disconnect()
            print(f"断开结果: {disconnect_result['message']}")
        else:
            print(f"获取设备详情失败: {current_device['message']}")
    else:
        print("设备连接失败")


def main():
    """主函数"""
    test_select_device()


if __name__ == "__main__":
    main() 