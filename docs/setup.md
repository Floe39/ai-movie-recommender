# 环境配置

项目使用 Python 3.11+、Node.js 20.19+ 和 SQLite。完整的 Windows CMD 启动命令见项目根目录 [README.md](../README.md)。

`.env` 需要配置：

```text
TMDB_API_KEY=你的TMDB密钥
DEEPSEEK_API_KEY=你的DeepSeek密钥
DASHSCOPE_API_KEY=你的百炼密钥
RAG_ENABLED=true
```

- `DEEPSEEK_API_KEY` 或 `DASHSCOPE_API_KEY` 至少配置一个，用于条件理解与推荐理由；
- 故事描述找片还需要 `DASHSCOPE_API_KEY`，并使用 `text-embedding-v4`；
- `.env` 不提交到 GitHub，提交前只保留 `.env.example`；
- `python backend\verify_services.py` 会用真实 Key 检查 TMDB、对话模型和 Embedding。
