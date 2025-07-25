#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
火山引擎语音合成使用示例
"""

import asyncio
import sys
import pathlib

# 添加项目根目录到Python路径
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from ..volcengine.tts_tool import VolcengineTTSTool


async def basic_example():
    """基础使用示例"""
    print("=" * 50)
    print("基础语音合成示例")
    print("=" * 50)
    
    # 初始化工具
    tts = VolcengineTTSTool()
    
    # 简单文本合成
    text = "你好，这是基础语音合成示例。"
    
    try:
        audio_data = await tts.synthesize_speech_async(
            text=text,
            output_file="basic_example.mp3"
        )
        
        print(f"✅ 合成成功，音频长度: {len(audio_data)} 字节")
        
    except Exception as e:
        print(f"❌ 合成失败: {e}")


if __name__ == "__main__":
    # 检查配置
    tts = VolcengineTTSTool()
    config_info = tts.get_config_info()
    
    if config_info["appid"] != "已设置" or config_info["token"] != "已设置":
        print("❌ 配置不完整，请先设置AppID和Token")
        print("   配置文件: tool/volcengine/config/tts.json")
        sys.exit(1)
    
    # 运行示例
    asyncio.run(basic_example())