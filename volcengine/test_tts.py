#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
火山引擎语音合成测试脚本
"""

import asyncio
import os
import sys
import pathlib

# 添加项目根目录到Python路径
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from ..volcengine.tts_tool import VolcengineTTSTool


async def test_tts_config():
    """测试TTS配置"""
    print("=" * 60)
    print("火山引擎语音合成配置测试")
    print("=" * 60)
    
    try:
        # 1. 初始化工具
        print("1. 初始化语音合成工具...")
        tts = VolcengineTTSTool()
        
        # 2. 显示配置信息
        print("\\n2. 当前配置信息:")
        tts.print_config()
        
        # 3. 检查环境变量
        print("\\n3. 检查环境变量:")
        volcengine_appid = os.environ.get("VOLCENGINE_TTS_APPID")
        volcengine_token = os.environ.get("VOLCENGINE_TTS_TOKEN")
        
        print(f"  VOLCENGINE_TTS_APPID: {'已设置' if volcengine_appid else '未设置'}")
        print(f"  VOLCENGINE_TTS_TOKEN: {'已设置' if volcengine_token else '未设置'}")
        
        # 4. 检查配置完整性
        print("\\n4. 配置完整性检查:")
        config_info = tts.get_config_info()
        
        appid_ok = config_info["appid"] == "已设置"
        token_ok = config_info["token"] == "已设置"
        
        print(f"  AppID: {'✅' if appid_ok else '❌'} {config_info['appid']}")
        print(f"  Token: {'✅' if token_ok else '❌'} {config_info['token']}")
        print(f"  集群: ✅ {config_info['cluster']}")
        print(f"  音色: ✅ {config_info['voice_type']}")
        print(f"  编码: ✅ {config_info['encoding']}")
        
        # 5. 显示可用音色
        print("\\n5. 可用音色:")
        tts.list_voices()
        
        # 6. 配置建议
        print("\\n6. 配置建议:")
        if not appid_ok or not token_ok:
            print("  ❌ 请设置AppID和Token:")
            print("     方法1: 在配置文件 tool/volcengine/config/tts.json 中设置")
            print("     方法2: 设置环境变量:")
            print("       export VOLCENGINE_TTS_APPID='your-appid'")
            print("       export VOLCENGINE_TTS_TOKEN='your-token'")
            print("\\n  获取AppID和Token:")
            print("     1. 访问 https://console.volcengine.com/speech/service/8")
            print("     2. 创建应用获取AppID") 
            print("     3. 申请语音合成服务获取Token")
        else:
            print("  ✅ 配置完整，可以开始使用语音合成功能")
            
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")


async def test_simple_synthesis():
    """测试简单语音合成"""
    print("\\n" + "=" * 60)
    print("简单语音合成测试")
    print("=" * 60)
    
    try:
        tts = VolcengineTTSTool()
        
        # 检查配置
        config_info = tts.get_config_info()
        if config_info["appid"] != "已设置" or config_info["token"] != "已设置":
            print("❌ AppID或Token未设置，跳过合成测试")
            return
        
        # 简单文本合成
        test_text = "你好，这是火山引擎语音合成测试。"
        print(f"测试文本: {test_text}")
        
        print("\\n开始语音合成...")
        audio_data = await tts.synthesize_speech_async(
            text=test_text,
            output_file="test_output.mp3",
            voice_type="BV001_streaming"  # 使用免费音色
        )
        
        if audio_data:
            print(f"\\n✅ 合成成功!")
            print(f"   音频长度: {len(audio_data)} 字节")
            print(f"   输出文件: test_output.mp3")
        else:
            print("❌ 未生成音频数据")
            
    except Exception as e:
        print(f"❌ 语音合成测试失败: {e}")


if __name__ == "__main__":
    print("火山引擎语音合成测试脚本")
    print("\\n选择测试模式:")
    print("1. 配置测试")
    print("2. 简单合成测试")
    print("3. 全部测试")
    
    try:
        choice = input("\\n请选择 (1-3): ").strip()
        
        if choice == "1":
            asyncio.run(test_tts_config())
        elif choice == "2":
            asyncio.run(test_simple_synthesis())
        elif choice == "3":
            asyncio.run(test_tts_config())
            asyncio.run(test_simple_synthesis())
        else:
            print("无效选择，默认运行配置测试")
            asyncio.run(test_tts_config())
            
    except KeyboardInterrupt:
        print("\\n\\n测试被用户中断")