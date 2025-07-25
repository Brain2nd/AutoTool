"""
微信工具包

提供微信会话归档、搜索、聊天缓存和管理功能
"""

# 定义要导出的工具列表
__all__ = []

# 基础工具导入
try:
    from .db.postgrestool import PostgresTool
    __all__.append('PostgresTool')
except ImportError:
    pass

try:
    from .cache.postgrescachetool import PostgresCacheTool
    __all__.append('PostgresCacheTool')
except ImportError:
    pass

try:
    from .browser.browsertool import BrowserTool
    __all__.append('BrowserTool')
except ImportError:
    pass

try:
    from .chat.postgreschattool import PostgresChatTool
    __all__.append('PostgresChatTool')
except ImportError:
    pass

# 可能依赖外部库的工具，使用条件导入
try:
    from .wx.AsyncWxTool import AsyncWxTool
    __all__.append('AsyncWxTool')
except ImportError:
    # 当wxautox库不可用时，不会导致整个模块导入失败
    AsyncWxTool = None

# RAG工具条件导入
try:
    from .rag.ragtool import RAGTool
    __all__.append('RAGTool')
except ImportError:
    RAGTool = None

# 如果RAGTool可用，添加到__all__
if RAGTool:
    __all__.append('RAGTool') 