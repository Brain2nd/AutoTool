"""
Web API模块

提供各种Web API服务：
- Gemini Chat API
"""

__all__ = []

# 可能依赖外部库的工具，使用条件导入
try:
    from .gemini_chat import GeminiChat
    __all__.append('GeminiChat')
except ImportError:
    pass
