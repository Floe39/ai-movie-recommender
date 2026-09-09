# 智能观影推荐与片单助手

用自然语言找电影：TMDB 提供真实影片数据和硬条件过滤；DeepSeek/百炼理解需求；RAG 用少量真实影片简介补充故事描述检索。

## 需要准备

- Python 3.11+、Node.js 20.19+；
- `TMDB_API_KEY`；
- `DEEPSEEK_API_KEY` 或 `DASHSCOPE_API_KEY`：用于对话模型；
- `DASHSCOPE_API_KEY`：RAG 向量检索必需，使用 `text-embedding-v4`。

真实 Key 只能放在 `.env`，不能放在 `.env.example`。

## 配置 `.env`

在项目根目录执行一次：

```cmd
copy .env.example .env
notepad .env
```

至少填写：

```text
TMDB_API_KEY=你的TMDB密钥
DEEPSEEK_API_KEY=你的DeepSeek密钥
DASHSCOPE_API_KEY=你的百炼密钥
RAG_ENABLED=true
```

`DEEPSEEK_API_KEY` 与 `DASHSCOPE_API_KEY` 可同时配置；默认优先使用 DeepSeek 做对话，百炼用于 Embedding。

## Windows CMD 启动

### 终端 1：后端

```cmd
cd /d D:\ai_project\ai-movie-recommender
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python backend\init_db.py
python backend\verify_services.py
python -m uvicorn app.api:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

### 终端 2：前端

```cmd
cd /d D:\ai_project\ai-movie-recommender\frontend
if not exist node_modules npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。

虚拟环境只用于 Python 后端；前端通过 `node_modules` 独立管理依赖。删除 `.venv`、`node_modules` 或升级依赖后，上面的命令会重新创建或安装。

## RAG 如何工作

1. 在“资料库”点击“导入演示影片简介”，后端从 TMDB 获取少量真实影片简介并写入 SQLite；
2. **条件检索**解析类型、时长、年份、评分等条件，并由 TMDB 真实数据筛选；
3. **故事描述检索**调用百炼 `text-embedding-v4` 将影片简介向量化，再按语义相似度检索。例如“小女孩和一匹狼的故事”可召回《小红帽》的简介；
4. RAG 有命中时只返回命中的电影，按命中资料数量、再按相似度排序，最多 10 部；命中不足 5 部时就只显示实际命中的数量，不补充无关电影；
5. TMDB 仍负责类型、时长、年份、评分等硬条件；
6. 结果卡片展示实际引用的简介片段与来源。

## 数据库与验证

`data/movie_recommender.db` 是真实 SQLite 数据库，包含影片缓存、片单、历史、每日推荐、影片简介和向量切块。`python backend\verify_services.py` 会实际检查 TMDB、对话模型和 Embedding 是否可用。

后端接口与数据模型见 [docs/design.md](docs/design.md)，完整环境说明见 [docs/setup.md](docs/setup.md)。
