"""
火山引擎AI服务模块

提供火山引擎相关的AI服务：
- TTS服务
"""

__all__ = []

# 可能依赖外部库的工具，使用条件导入
try:
    from .volcenginetool import VolcengineTool
    __all__.append('VolcengineTool')
except ImportError:
    pass

try:
    from .tts_tool import TTSTool
    __all__.append('TTSTool')
except ImportError:
    pass
