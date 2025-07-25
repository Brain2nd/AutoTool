# AutoTool - 自动化工具集

AutoTool 是一个功能强大的 Python 自动化工具库，提供了浏览器自动化、AI 聊天集成、数据库操作、移动设备控制等多种自动化功能。

## 功能特性

### 🌐 浏览器自动化
- 基于 Chrome DevTools 协议的浏览器控制
- 元素查找和交互
- 页面截图和导航
- DOM 分析和操作

### 🤖 AI 聊天集成
- 支持多种 AI 模型：Gemini、豆包、Grok 等
- 智能对话模板系统
- 聊天历史管理
- 多平台 AI 接口封装

### 📱 移动设备控制
- Android 设备自动化（基于 ADB）
- UI 元素识别和操作
- 应用启动和管理
- 屏幕截图和分析

### 💬 社交平台集成
- 微信自动化工具
- 飞书（Lark）集成
- 群聊管理和消息处理

### 🗄️ 数据库工具
- PostgreSQL 集成
- 数据缓存管理
- 白名单系统
- 聊天记录存储

### 🔍 AI 增强功能
- RAG（检索增强生成）
- 文本重排序
- 向量嵌入
- 智能搜索

### 🎵 语音服务
- 火山引擎 TTS 集成
- 语音合成和播放

## 模块结构

```
autotool/
├── browser/          # 浏览器自动化
├── chat/            # AI 聊天工具
├── chatdoubao/      # 豆包聊天集成
├── chatgemini/      # Gemini 聊天集成
├── chatgeminipro/   # Gemini Pro 聊天集成
├── chatgork/        # Grok 聊天集成
├── db/              # 数据库工具
├── lark/            # 飞书集成
├── ppadb/           # Android 设备控制
├── wx/              # 微信自动化
├── volcengine/      # 火山引擎服务
├── rag/             # 检索增强生成
├── rerank/          # 文本重排序
├── emb/             # 向量嵌入
├── webapi/          # Web API 工具
└── cache/           # 缓存管理
```

## 安装

```bash
pip install autotool
```

或者从源码安装：

```bash
git clone https://github.com/Brain2nd/AutoTool.git
cd AutoTool
pip install -e .
```

## 快速开始

### 浏览器自动化示例

```python
from autotool.browser import browsertool

# 启动浏览器并导航到页面
browser = browsertool.BrowserTool()
browser.navigate_to_url("https://example.com")
browser.screenshot("example.png")
```

### AI 聊天示例

```python
from autotool.chat import postgreschattool

# 初始化聊天工具
chat = postgreschattool.PostgresChatTool()
response = chat.chat("你好，请介绍一下自己")
print(response)
```

### 数据库操作示例

```python
from autotool.db import postgrestool

# 连接数据库
db = postgrestool.PostgresTool()
db.connect()
results = db.query("SELECT * FROM users")
```

## 配置

大多数模块都支持配置文件，通常位于各模块的 `config/` 目录下。你可以根据需要修改相应的 JSON 配置文件。

详细配置说明请参见 [CONFIG.md](CONFIG.md)。

## 贡献

欢迎提交 Pull Request 和 Issue！

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 联系方式

- 项目主页：https://github.com/Brain2nd/AutoTool
- 问题反馈：https://github.com/Brain2nd/AutoTool/issues

## 更新日志

### v1.0.0
- 首次发布
- 包含所有核心功能模块
- 支持多平台自动化操作 