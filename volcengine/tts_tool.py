#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
火山引擎语音合成工具

基于火山引擎大模型语音合成API实现文本转语音功能
"""

import os
import json
import uuid
import struct
import base64
import asyncio
import pathlib
import websockets
from typing import Optional, Dict, Any, Tuple


class VolcengineTTSTool:
    """火山引擎语音合成工具类"""
    
    def __init__(self, config_name: str = "tts"):
        """
        初始化语音合成工具
        
        Args:
            config_name: 配置文件名（不含扩展名）
        """
        self.config = self._load_config(config_name)
        self.ws_url = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"
        
    def _load_config(self, config_name: str) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_name: 配置文件名
            
        Returns:
            配置字典
        """
        current_dir = pathlib.Path(__file__).parent
        config_path = current_dir / "config" / f"{config_name}.json"
        
        if not config_path.exists():
            # 创建默认配置
            default_config = {
                "appid": "",
                "token": "",
                "cluster": "volcano_tts",
                "voice_type": "zh_male_M392_conversation_wvae_bigtts",
                "encoding": "mp3",
                "speed_ratio": 1.0,
                "language": "zh",
                "pitch_ratio": 1.0,
                "volume_ratio": 1.0,
                "silence_duration": 125,
                "with_frontend": 1,
                "pure_english_opt": 1
            }
            
            config_path.parent.mkdir(exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=4)
            
            return default_config
        
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _get_credentials(self) -> Tuple[str, str]:
        """
        获取认证信息
        
        Returns:
            (appid, token) 元组
        """
        # 优先使用配置文件
        appid = self.config.get("appid", "")
        token = self.config.get("token", "")
        
        # 如果配置文件为空，尝试从环境变量获取
        if not appid:
            appid = os.environ.get("VOLCENGINE_TTS_APPID", "")
        if not token:
            token = os.environ.get("VOLCENGINE_TTS_TOKEN", "")
            
        return appid, token
    
    def _create_binary_frame(self, json_data: str) -> bytes:
        """
        创建二进制协议帧
        
        Args:
            json_data: JSON格式的请求数据
            
        Returns:
            二进制帧数据
        """
        # 根据文档，我们使用简化的二进制协议
        # 协议版本(4) + 报头大小(4) + 消息类型(4) + 标志(4) + 序列化(4) + 压缩(4) + 保留(8)
        
        # 第一个字节: 协议版本(0001) + 报头大小(0001) 
        byte1 = 0x11  # 0001 0001
        
        # 第二个字节: 消息类型(0001) + 标志(0000)
        byte2 = 0x10  # 0001 0000
        
        # 第三个字节: 序列化方法(0001) + 压缩方法(0000)
        byte3 = 0x10  # 0001 0000
        
        # 第四个字节: 保留字段
        byte4 = 0x00
        
        # 构建头部 (4字节)
        header = struct.pack(">BBBB", byte1, byte2, byte3, byte4)
        
        # 添加payload大小（4字节，大端序）
        json_bytes = json_data.encode("utf-8")
        payload_size = len(json_bytes)
        
        # 构建完整帧: 头部 + payload大小 + payload
        frame = header + struct.pack(">I", payload_size) + json_bytes
        
        return frame
    
    def _create_request_data(self, text: str, **kwargs) -> str:
        """
        创建请求数据
        
        Args:
            text: 要合成的文本
            **kwargs: 其他参数覆盖
            
        Returns:
            JSON格式的请求数据
        """
        appid, token = self._get_credentials()
        
        # 基础请求结构
        request_data = {
            "app": {
                "appid": appid,
                "token": token,
                "cluster": self.config.get("cluster", "volcano_tts")
            },
            "user": {
                "uid": kwargs.get("uid", "default_user")
            },
            "audio": {
                "voice_type": kwargs.get("voice_type", self.config.get("voice_type")),
                "encoding": kwargs.get("encoding", self.config.get("encoding", "mp3")),
                "speed_ratio": kwargs.get("speed_ratio", self.config.get("speed_ratio", 1.0)),
                "language": kwargs.get("language", self.config.get("language", "zh")),
                "pitch_ratio": kwargs.get("pitch_ratio", self.config.get("pitch_ratio", 1.0)),
                "volume_ratio": kwargs.get("volume_ratio", self.config.get("volume_ratio", 1.0)),
                "silence_duration": kwargs.get("silence_duration", self.config.get("silence_duration", 125)),
                "with_frontend": kwargs.get("with_frontend", self.config.get("with_frontend", 1)),
                "pure_english_opt": kwargs.get("pure_english_opt", self.config.get("pure_english_opt", 1))
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "operation": "submit"
            }
        }
        
        return json.dumps(request_data, ensure_ascii=False)
    
    async def synthesize_speech_async(self, text: str, output_file: Optional[str] = None, **kwargs) -> bytes:
        """
        异步语音合成
        
        Args:
            text: 要合成的文本
            output_file: 输出文件路径（可选）
            **kwargs: 其他参数
            
        Returns:
            音频数据字节
        """
        if not text or not text.strip():
            raise ValueError("文本不能为空")
        
        appid, token = self._get_credentials()
        if not appid or not token:
            raise ValueError("请设置appid和token，可以在配置文件中设置或使用环境变量VOLCENGINE_TTS_APPID和VOLCENGINE_TTS_TOKEN")
        
        print(f"开始语音合成: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        # 创建请求数据
        request_json = self._create_request_data(text, **kwargs)
        request_frame = self._create_binary_frame(request_json)
        
        # 准备认证头
        headers = {
            "Authorization": f"Bearer;{token}"
        }
        
        audio_data = b""
        
        try:
            print(f"正在连接到语音合成服务...")
            async with websockets.connect(self.ws_url, extra_headers=headers) as websocket:
                print(f"连接成功，发送合成请求...")
                
                # 发送请求
                await websocket.send(request_frame)
                
                # 接收响应
                response_count = 0
                while True:
                    try:
                        response = await websocket.recv()
                        response_count += 1
                        
                        if isinstance(response, bytes):
                            # 处理二进制响应
                            if len(response) >= 8:  # 至少包含头部(4字节) + payload大小(4字节)
                                # 跳过头部，读取payload大小
                                payload_size = struct.unpack(">I", response[4:8])[0]
                                
                                if len(response) >= 8 + payload_size:
                                    # 提取JSON数据
                                    json_data = response[8:8+payload_size].decode("utf-8")
                                    response_obj = json.loads(json_data)
                                    
                                    code = response_obj.get('code', 0)
                                    sequence = response_obj.get('sequence', 0)
                                    
                                    print(f"收到响应 {response_count}: code={code}, sequence={sequence}")
                                    
                                    if code == 3000:
                                        # 成功响应
                                        data = response_obj.get("data", "")
                                        if data:
                                            # 解码base64音频数据
                                            chunk_audio = base64.b64decode(data)
                                            audio_data += chunk_audio
                                            print(f"  接收音频数据: {len(chunk_audio)} 字节")
                                        
                                        # 检查是否完成
                                        if sequence < 0:
                                            print(f"语音合成完成！总长度: {len(audio_data)} 字节")
                                            break
                                    else:
                                        # 错误响应
                                        error_msg = response_obj.get("message", "未知错误")
                                        raise Exception(f"语音合成失败 (错误码: {code}): {error_msg}")
                        else:
                            # 文本响应
                            try:
                                response_obj = json.loads(response)
                                print(f"收到文本响应: {response_obj}")
                            except:
                                print(f"收到未知响应: {response}")
                            
                    except websockets.exceptions.ConnectionClosed:
                        print("WebSocket连接已关闭")
                        break
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误: {e}")
                        continue
                    except Exception as e:
                        print(f"处理响应时出错: {e}")
                        break
                        
        except Exception as e:
            print(f"语音合成过程中出错: {e}")
            raise
        
        # 保存到文件
        if output_file and audio_data:
            output_path = pathlib.Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            print(f"音频已保存到: {output_path}")
        
        return audio_data
    
    def synthesize_speech(self, text: str, output_file: Optional[str] = None, **kwargs) -> bytes:
        """
        同步语音合成
        
        Args:
            text: 要合成的文本
            output_file: 输出文件路径（可选）
            **kwargs: 其他参数
            
        Returns:
            音频数据字节
        """
        return asyncio.run(self.synthesize_speech_async(text, output_file, **kwargs))
    
    def get_available_voices(self) -> Dict[str, str]:
        """
        获取可用的音色列表
        
        Returns:
            音色代码到描述的映射
        """
        # 基于文档的一些常用音色
        voices = {
            "zh_male_M392_conversation_wvae_bigtts": "中文男声-对话音色",
            "zh_female_F398_conversation_wvae_bigtts": "中文女声-对话音色", 
            "en_male_M301_conversation_wvae_bigtts": "英文男声-对话音色",
            "en_female_F302_conversation_wvae_bigtts": "英文女声-对话音色",
            "BV001_streaming": "基础男声-流式音色（免费）",
            "BV002_streaming": "基础女声-流式音色（免费）"
        }
        return voices
    
    def list_voices(self) -> None:
        """打印可用音色列表"""
        print("\\n可用音色列表:")
        print("=" * 60)
        for voice_id, description in self.get_available_voices().items():
            print(f"  {voice_id}")
            print(f"    {description}")
            print()
        print("=" * 60)
    
    def get_config_info(self) -> Dict[str, Any]:
        """
        获取当前配置信息
        
        Returns:
            配置信息字典
        """
        appid, token = self._get_credentials()
        return {
            "appid": "已设置" if appid else "未设置",
            "token": "已设置" if token else "未设置", 
            "cluster": self.config.get("cluster"),
            "voice_type": self.config.get("voice_type"),
            "encoding": self.config.get("encoding"),
            "speed_ratio": self.config.get("speed_ratio"),
            "language": self.config.get("language")
        }
    
    def print_config(self) -> None:
        """打印当前配置"""
        print("\\n当前配置:")
        print("=" * 40)
        config_info = self.get_config_info()
        for key, value in config_info.items():
            print(f"  {key}: {value}")
        print("=" * 40)


# 使用示例
async def example_usage():
    """使用示例"""
    print("火山引擎语音合成工具示例")
    print("=" * 50)
    
    # 初始化工具
    tts = VolcengineTTSTool()
    
    # 显示配置
    tts.print_config()
    
    # 列出可用音色
    tts.list_voices()
    
    # 语音合成示例
    text = "你好，这是火山引擎语音合成测试。"
    print(f"\\n合成文本: {text}")
    
    try:
        audio_data = await tts.synthesize_speech_async(
            text=text,
            output_file="output.mp3",
            voice_type="zh_male_M392_conversation_wvae_bigtts",
            speed_ratio=1.0
        )
        
        print(f"\\n✅ 合成成功！")
        print(f"   音频长度: {len(audio_data)} 字节")
        print(f"   输出文件: output.mp3")
        
    except Exception as e:
        print(f"\\n❌ 合成失败: {e}")
        print("\\n请检查:")
        print("   1. 配置文件中的appid和token是否正确")
        print("   2. 网络连接是否正常")
        print("   3. 是否有足够的API配额")


if __name__ == "__main__":
    asyncio.run(example_usage())