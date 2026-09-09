"""用真实 API Key 检查 TMDB 与已选择的 LLM 是否可用，不会写入 SQLite。

从项目根目录运行：python backend/verify_services.py
需要 .env 中存在 TMDB_API_KEY，且至少存在一个 LLM API Key。
"""

import asyncio

from app.llm import LLMClient
from app.embeddings import EmbeddingClient
from app.schemas import MovieSearchQuery
from app.tmdb import TMDBClient


async def main() -> None:
    tmdb = TMDBClient()
    try:
        # 真实请求 1：先取得一部可信候选，再读取详情，验证两类 TMDB 接口均可用。
        movie_ids = await tmdb.discover(MovieSearchQuery(genres=["comedy"]))
        if not movie_ids:
            raise RuntimeError("TMDB 返回了空候选，无法完成连通性验证")
        movie, _ = await tmdb.movie_detail(movie_ids[0])
        print(f"TMDB 连接成功：{movie.title} (TMDB #{movie.tmdb_id})")
    finally:
        await tmdb.close()

    # 真实请求 2：验证当前 LLM Provider 能按项目输出契约返回结构化条件。
    llm = LLMClient()
    conditions = await llm.parse_conditions("推荐一部两小时以内的轻松喜剧")
    print(f"LLM 连接成功：provider={llm.provider}, parsed_conditions={conditions.model_dump()}")

    # 真实请求 3：确认 RAG 所用的百炼 Embedding 模型和向量维度可用。
    embedding = EmbeddingClient()
    vector = (await embedding.embed(["治愈但不幼稚的电影"]))[0]
    print(f"Embedding 连接成功：dimensions={len(vector)}")


if __name__ == "__main__":
    asyncio.run(main())
