import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Base
from app.rag import RAGService


class FakeEmbeddings:
    """固定二维向量，避免测试调用真实百炼服务。"""
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] if "治愈" in text else [0.0, 1.0] for text in texts]


def test_movie_synopsis_is_indexed_and_retrieved():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = Settings(database_url="sqlite:///:memory:", dashscope_api_key="test-key")
    with Session(engine) as db:
        rag = RAGService(db, embeddings=FakeEmbeddings(), settings=settings)
        rag.repo.upsert_synopsis(42, "测试影片", "这是一部温柔而治愈的成长电影。", "https://example.test/movie/42")
        asyncio.run(rag._index("tmdb_synopsis", "42", "这是一部温柔而治愈的成长电影。", 42))
        citations = asyncio.run(rag.search_synopses_vector("想找治愈一点的电影"))

        assert citations[42][0].source_name == "TMDB 简介 · 测试影片"
        assert citations[42][0].similarity == 1
        assert rag.status()[-1] == 1
