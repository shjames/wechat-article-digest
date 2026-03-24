# WeChat Article Summary Skill

## 基本信息

- **技能名称**：WeChat Article Summary
- **版本**：1.0.0
- **描述**：一个用于抓取微信公众号最近文章并调用大模型自动生成摘要的 Skill，支持多种大模型提供商。
- **适用平台**：OpenClaw、Trae AI 等 Agent/Skill 平台

## 核心特性

- **统一模型调用架构**：支持多种大模型提供商（OpenAI、Anthropic、Google Gemini）
- **智能缓存机制**：减少 API 调用，降低成本
- **安全边界控制**：防止滥用和异常情况
- **自动执行模式**：无需用户交互，默认单次执行

## 触发条件

### 自动触发
- 定时执行：根据配置的时间间隔自动执行
- 系统启动时：可配置为系统启动后自动执行

### 手动触发
- 直接运行：`python wechat_summary.py`
- Agent 平台调用：通过平台 API 调用

## 输入参数

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
|-------|------|------|------|--------|
| `wechat_api.api_key` | string | 是 | 微信文章抓取 API 密钥 | - |
| `official_accounts` | array | 是 | 要抓取的公众号名称列表 | - |
| `llm.sdk_type` | string | 是 | 大模型 SDK 类型 | - |
| `llm.model` | string | 是 | 大模型名称 | - |
| `llm.api_key` | string | 是 | 大模型 API 密钥 | - |
| `llm.base_url` | string | 否 | 大模型 API 基础 URL | - |
| `interval` | integer | 否 | 定时执行间隔（分钟） | 60 |
| `article_limit` | integer | 否 | 每公众号文章数量限制 | 5 |

## 输出结果

- **主要输出**：`wechat_articles_summary.md`（Markdown 格式的文章总结）
- **缓存文件**：`./cache/` 目录下的缓存文件
- **日志输出**：控制台日志，包含执行状态和错误信息

## 安全边界

1. **API 密钥保护**：
   - API 密钥存储在本地配置文件中，不向外部传输
   - 禁止在日志中打印 API 密钥
   - 建议使用环境变量或加密存储敏感信息

2. **请求频率限制**：
   - 对微信 API 的调用频率进行控制，避免被封禁
   - 对大模型 API 的调用进行缓存，减少请求次数

3. **输入验证**：
   - 验证公众号名称格式
   - 验证 API 密钥格式
   - 验证配置文件格式

4. **异常处理**：
   - API 调用失败时的优雅降级
   - 网络异常时的重试机制
   - 使用缓存数据作为 fallback

5. **资源限制**：
   - 限制每公众号的文章数量
   - 限制文章内容长度
   - 限制大模型输出 token 数量

## 配置说明

### 配置文件示例（config.json）

```json
{
  "wechat_api": {
    "provider": "dajiala",
    "api_key": "your_wechat_api_key"
  },
  "official_accounts": [
    "数字生命卡兹克",
    "刘润"
  ],
  "interval": 60,
  "article_limit": 5,
  "llm": {
    "sdk_type": "anthropic",
    "model": "MiniMax-M2.7",
    "api_key": "your_llm_api_key",
    "base_url": "https://api.minimax.io/anthropic"
  }
}
```

### 支持的 LLM SDK 类型

- `openai`：OpenAI 兼容 API（如 OpenAI、DeepSeek、Moonshot 等）
- `anthropic`：Anthropic 兼容 API（如 Claude、MiniMax 等）
- `gemini`：Google Gemini API

## 依赖项

### Python 包
- `requests`：用于 HTTP 请求
- `schedule`：用于定时任务
- `openai`：用于 OpenAI 兼容 API（可选）
- `anthropic`：用于 Anthropic 兼容 API（可选）
- `google-generativeai`：用于 Google Gemini API（可选）

### 外部服务
- 微信文章抓取 API（如 dajiala）
- 大模型 API（如 OpenAI、Anthropic、Google Gemini）

## 使用示例

### 基本使用

1. 配置 `config.json` 文件
2. 运行 `python wechat_summary.py`
3. 查看生成的 `wechat_articles_summary.md` 文件

### 在 OpenClaw 中使用

```python
from skills.wechat_summary import WeChatSummary

# 初始化
wechat_summary = WeChatSummary()

# 执行任务
wechat_summary.run_once()

# 获取结果
with open('wechat_articles_summary.md', 'r', encoding='utf-8') as f:
    summary = f.read()
print(summary)
```

## 故障排除

### 常见问题

1. **API 调用失败**
   - 检查 API 密钥是否正确
   - 检查网络连接
   - 查看控制台错误信息

2. **缓存不生效**
   - 检查 `./cache` 目录权限
   - 检查缓存文件是否存在
   - 查看控制台缓存相关日志

3. **文章获取失败**
   - 检查公众号名称是否正确
   - 检查 API 密钥是否有效
   - 检查网络连接

### 错误码

| 错误码 | 描述 | 解决方案 |
|-------|------|----------|
| 401 | API 密钥无效 | 检查 API 密钥是否正确 |
| 403 | API 调用频率限制 | 减少调用频率，使用缓存 |
| 404 | 公众号不存在 | 检查公众号名称是否正确 |
| 500 | 服务器错误 | 稍后重试，检查网络连接 |

## 性能优化

1. **缓存策略**：
   - 文章列表缓存（1小时有效期）
   - 文章内容缓存（永久）
   - 总结结果缓存（永久）

2. **API 调用优化**：
   - 批量获取文章
   - 优先使用缓存数据
   - 失败时使用过期缓存

3. **资源使用优化**：
   - 限制并发请求数
   - 合理设置超时时间
   - 优化内存使用

## 版本历史

- **v1.0.0**：初始版本
  - 支持多种大模型
  - 实现智能缓存
  - 增加安全边界
  - 优化自动执行模式
