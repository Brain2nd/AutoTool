"""
微信聊天工具模块

提供与大语言模型的聊天集成功能，支持：
- 文本对话
- 多模态对话（图片、音频）
- 会话管理和历史记录
- 多种AI模型接口（Gemini、OpenAI等）
"""

from .postgreschattool import PostgresChatTool

__all__ = [
    'PostgresChatTool'
] 