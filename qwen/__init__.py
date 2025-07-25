"""
Qwen AI模型工具模块

提供通义千问AI模型相关的功能：
- QwenTool: 通义千问API封装
"""

__all__ = []

# 可能依赖外部库的工具，使用条件导入
try:
    from .qwentool import QwenTool
    __all__.append('QwenTool')
except ImportError:
    pass 