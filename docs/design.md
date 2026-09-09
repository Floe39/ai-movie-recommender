# 当前系统设计

## 模块

```text
Vue 3 前端
  ├── 条件找片 / 故事描述找片
  ├── 今日推荐、影片详情、片单与推荐历史
  └── 影片简介库
          │ HTTP
FastAPI 后端
  ├── LLM：提取条件、生成推荐理由
  ├── TMDB：发现影片、详情、海报与评分
  ├── RAG：导入少量真实影片简介并进行向量检索
  └── SQLite：缓存、片单、历史、每日推荐与 RAG 向量
```

## 推荐流程

1. **按类型、时长等条件找**：DeepSeek 或百炼从输入中提取类型、时长、年份与评分条件；后端用 TMDB 查询，并以详情字段复核硬条件。
2. **按故事描述找**：在“影片简介库”导入少量真实 TMDB 简介；百炼 `text-embedding-v4` 对简介与用户故事描述生成向量，按命中数量和相似度排序。
3. 故事描述模式只显示 RAG 命中的电影，最多 10 部；条件模式从符合条件的 TMDB 候选中随机挑选，最多 10 部。
4. 推荐理由只基于当前候选的 TMDB 字段及实际引用的简介片段生成。

## 今日推荐

首次打开首页时，从评分不低于 7 分的 TMDB 候选中生成 5 部推荐，写入 SQLite 的 `daily_recommendations`。同一天直接读取本地缓存，次日重新生成。

## 数据表

| 表 | 用途 |
| --- | --- |
| `movies` | TMDB 影片详情缓存 |
| `watchlist_items` | 想看、已看片单与短评 |
| `recommendation_history` | 用户需求、解析条件与结果 ID |
| `daily_recommendations` | 当日首页推荐的影片 ID |
| `movie_synopses` | 演示用真实影片简介 |
| `rag_chunks` | 简介文本切块与 Embedding 向量 |

字段说明见 [data/README.md](../data/README.md)。

## 已实现接口

| 方法与路径 | 用途 |
| --- | --- |
| `POST /api/recommendations` | 条件或故事描述找片 |
| `GET /api/movies/today` | 获取当天缓存的今日推荐 |
| `GET /api/movies/{tmdb_id}` | 获取影片详情 |
| `GET/POST/PATCH/DELETE /api/watchlist` | 管理片单 |
| `GET /api/recommendations/history` | 获取推荐历史 |
| `GET /api/rag/status` | 查询影片简介库状态 |
| `POST /api/rag/demo-synopses/seed` | 导入演示影片简介并建立向量 |
