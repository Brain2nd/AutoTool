"""
Poe API模块

提供Poe AI聊天服务：
- Poe Chat API
"""

__all__ = []

# 可能依赖外部库的工具，使用条件导入
try:
    from .poe_chat import PoeChat
    __all__.append('PoeChat')
except ImportError:
    pass
