# 配置说明

## API 密钥配置

为了使用 AutoTool 的各种 AI 功能，你需要在相应的配置文件中设置 API 密钥。

### 需要配置的 API 密钥

#### 1. OpenAI API 密钥
- 文件位置：
  - `chat/config/default.json`
  - `chat/config/gemini.json`
  - `chatdoubao/config/default.json`
  - `chatdoubao/config/gemini.json`
  - `chatgeminipro/config/default.json`
- 替换：`"YOUR_OPENAI_API_KEY_HERE"` → 你的实际 OpenAI API 密钥

#### 2. Google Gemini API 密钥
- 文件位置：`chatgemini/config/default.json`
- 替换：`"YOUR_GOOGLE_GEMINI_API_KEY_HERE"` → 你的 Google Gemini API 密钥

#### 3. xAI (Grok) API 密钥
- 文件位置：
  - `chatgemini/config/default copy.json`
  - `chatgork/config/default.json`
- 替换：`"YOUR_XAI_API_KEY_HERE"` → 你的 xAI API 密钥

#### 4. 豆包 (Doubao) API 密钥
- 文件位置：`chatdoubao/config/doubao.json`
- 替换：`"YOUR_DOUBAO_API_KEY_HERE"` → 你的豆包 API 密钥

#### 5. 通义千问 (Qwen) API 密钥
- 文件位置：`qwen/config/default.json`
- 替换：`"YOUR_QWEN_API_KEY_HERE"` → 你的阿里云通义千问 API 密钥

#### 6. Jina AI API 密钥
- 文件位置：
  - `emb/config/default.json`
  - `rag/config/default.json`
  - `rerank/config/default.json`
- 替换：`"YOUR_JINA_API_KEY_HERE"` → 你的 Jina AI API 密钥

#### 7. 数据库配置
- 数据库主机：`"YOUR_DATABASE_HOST_HERE"` → 你的数据库主机地址
- 数据库端口：`"YOUR_DATABASE_PORT_HERE"` → 你的数据库端口
- 数据库用户：`"YOUR_DATABASE_USER_HERE"` → 你的数据库用户名
- 数据库密码：`"YOUR_DATABASE_PASSWORD_HERE"` → 你的数据库密码
- 数据库名称：`"YOUR_DATABASE_NAME_HERE"` → 你的数据库名称

#### 8. 业务配置
- 团长活动ID：`"YOUR_TEAM_ACTIVITY_ID_HERE"` → 你的团长活动ID（在相关TXT模板文件中）

#### 9. 火山引擎TTS配置
- 文件位置：`volcengine/config/tts.json`
- 需要设置：`appid` 和 `token` 字段

### 本地 Ollama 配置
- 文件位置：
  - `chat/config/local.json`
  - `chatdoubao/config/local.json`
- 这些文件使用本地 Ollama，API 密钥设置为 `"not-needed-for-ollama"`，无需修改。

### 空白配置
- 文件位置：`rag/config/rerank.json`
- API 密钥为空字符串 `""`，根据需要设置。

## 使用说明

1. 获取相应服务的 API 密钥
2. 在对应的配置文件中替换占位符
3. 根据需要修改其他配置参数（如模型名称、温度等）
4. 保存文件并开始使用

## 注意事项

- 请妥善保管你的 API 密钥，不要提交到公共代码仓库
- 不同的模块可能使用不同的配置文件，请确保配置正确的文件
- 某些服务可能需要额外的配置参数，请参考相应服务的文档
