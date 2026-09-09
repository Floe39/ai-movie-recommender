# SQLite 数据库说明

数据库文件为 `movie_recommender.db`。首次运行项目时执行：

```cmd
python backend\init_db.py
```

系统会自动创建所有表。数据库使用 SQLite，当前为匿名单用户模式；表之间以 TMDB 影片 ID 进行业务关联，第一版没有设置 SQLite 外键约束。

## 表结构

### `movies`：影片缓存

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `tmdb_id` | INTEGER，主键 | TMDB 影片 ID |
| `title` | VARCHAR(300) | 影片标题 |
| `overview` | TEXT，可空 | TMDB 影片简介 |
| `poster_path` | VARCHAR(300)，可空 | TMDB 海报相对路径 |
| `release_year` | INTEGER，可空 | 上映年份 |
| `runtime_minutes` | INTEGER，可空 | 时长（分钟） |
| `genres_json` | TEXT | 类型数组 JSON |
| `vote_average` | FLOAT，可空 | TMDB 平均评分 |
| `popularity` | FLOAT，可空 | TMDB 热度值 |
| `updated_at` | DATETIME | 缓存更新时间 |

### `watchlist_items`：想看 / 已看片单

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | INTEGER，主键 | 片单记录 ID |
| `movie_tmdb_id` | INTEGER，唯一、索引 | 对应 `movies.tmdb_id`；同一影片只能加入一次 |
| `status` | VARCHAR(30) | `want_to_watch`（想看）或 `watched`（已看） |
| `note` | TEXT，可空 | 用户短评或备注 |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 最后修改时间 |

### `recommendation_history`：推荐历史

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | INTEGER，主键 | 历史记录 ID |
| `query` | TEXT | 原始自然语言需求或筛选说明 |
| `parsed_conditions_json` | TEXT | 后端解析后的筛选条件 JSON |
| `movie_tmdb_ids_json` | TEXT | 本次结果的 TMDB 影片 ID 数组 JSON |
| `created_at` | DATETIME | 创建时间 |

### `daily_recommendations`：每日推荐缓存

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `day` | VARCHAR(10)，主键 | 推荐日期，格式为 `YYYY-MM-DD` |
| `movie_tmdb_ids_json` | TEXT | 当天 5 部推荐的 TMDB 影片 ID 数组 JSON |
| `created_at` | DATETIME | 当天片单首次生成时间 |

首页首次读取“今日推荐”时才访问 TMDB 并写入此表；当天后续刷新直接读取 SQLite，次日自动生成新的片单。

### `movie_synopses`：RAG 演示影片简介

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `tmdb_id` | INTEGER，主键 | TMDB 影片 ID |
| `title` | VARCHAR(300) | 影片标题 |
| `overview` | TEXT | 从 TMDB 获取的真实影片简介 |
| `source_url` | VARCHAR(500) | 对应 TMDB 详情页链接 |
| `updated_at` | DATETIME | 导入或更新的时间 |

在“影片简介库”导入演示简介后，该表写入少量真实影片简介；配置百炼后，简介的向量会写入 `rag_chunks`。

### `rag_chunks`：RAG 向量索引

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | INTEGER，主键 | 文本切块 ID |
| `source_type` | VARCHAR(30)，索引 | 当前固定为 `tmdb_synopsis` |
| `source_id` | VARCHAR(120)，索引 | 来源记录的 ID |
| `movie_tmdb_id` | INTEGER，可空、索引 | 可选关联的 TMDB 影片 ID |
| `content` | TEXT | 用于检索的文本切块 |
| `embedding_json` | TEXT | 百炼 `text-embedding-v4` 返回的向量 JSON |
| `created_at` | DATETIME | 建立索引的时间 |

## 关系概览

```text
movies.tmdb_id ──────── watchlist_items.movie_tmdb_id
       │
       ├─────────────── movie_synopses.tmdb_id
       └─────────────── rag_chunks.movie_tmdb_id（可选）

recommendation_history：以 JSON 保存一次推荐的条件和结果 ID 列表
```

`.env` 不会写入数据库。若数据库包含你的片单或历史，不建议提交到 GitHub；保留 `data/.gitkeep` 和本说明即可，其他主机运行初始化命令会得到空数据库。
