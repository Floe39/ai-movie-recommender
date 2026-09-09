import json
import math

from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .embeddings import EmbeddingClient
from .models import MovieSynopsis
from .repository import Repository
from .schemas import RagCitation


class RAGService:
    """管理资料入库、向量检索及可追溯引用；不负责影片事实与硬条件。"""

    def __init__(self, db: Session, embeddings: EmbeddingClient | None = None, settings: Settings | None = None):
        self.repo = Repository(db)
        self.settings = settings or get_settings()
        self.embeddings = embeddings

    @property
    def is_configured(self) -> bool:
        return self.settings.rag_enabled and bool(self.settings.dashscope_api_key)

    def status(self) -> tuple[bool, bool, int, int, int]:
        synopsis_count, chunk_count = self.repo.rag_counts()
        return self.settings.rag_enabled, self.is_configured, synopsis_count, chunk_count

    async def seed_demo_synopses(self, tmdb) -> tuple[int, int]:
        """从 TMDB 拉取少量真实简介，作为项目演示用 RAG 语料。"""
        # 小红帽、狼行者、奇幻森林、少年派：覆盖童话、狼、成长、冒险等语义。
        demo_movie_ids = [109445, 441130, 278927, 87827]
        imported_movies = indexed_chunks = 0
        for tmdb_id in demo_movie_ids:
            movie, _ = await tmdb.movie_detail(tmdb_id)
            if not movie.overview:
                continue
            self.repo.upsert_synopsis(movie.tmdb_id, movie.title, movie.overview, movie.tmdb_url)
            # 条件检索不需要简介；有百炼 Key 时才建立故事描述检索所需的向量索引。
            if self.is_configured:
                indexed_chunks += await self._index("tmdb_synopsis", str(movie.tmdb_id), movie.overview, movie.tmdb_id)
            imported_movies += 1
        return imported_movies, indexed_chunks

    async def search_synopses_vector(self, query: str) -> dict[int, list[RagCitation]]:
        """向量模式：在已导入的真实影片简介中按语义召回。"""
        chunks = [chunk for chunk in self.repo.list_chunks() if chunk.source_type == "tmdb_synopsis"]
        if not self.is_configured or not chunks:
            return {}
        query_embedding = (await self._client().embed([query]))[0]
        matches: dict[int, list[RagCitation]] = {}
        for chunk in chunks:
            score = self._cosine(query_embedding, [float(value) for value in json.loads(chunk.embedding_json)])
            if chunk.movie_tmdb_id is None:
                continue
            source_name, source_url = self._source_metadata(chunk.source_type, chunk.source_id)
            matches.setdefault(chunk.movie_tmdb_id, []).append(RagCitation(
                source_type=chunk.source_type, source_name=source_name, source_url=source_url,
                excerpt=self._excerpt(chunk.content), similarity=max(0, min(score, 1)),
            ))
        return {movie_id: sorted(citations, key=lambda item: item.similarity, reverse=True)[:self.settings.rag_top_k]
                for movie_id, citations in matches.items()}

    async def _index(self, source_type: str, source_id: str, content: str, movie_tmdb_id: int | None) -> int:
        chunks = self._split(content)
        vectors = await self._client().embed(chunks)
        return self.repo.replace_chunks(source_type, source_id, list(zip(chunks, vectors, [movie_tmdb_id] * len(chunks))))

    def _client(self) -> EmbeddingClient:
        return self.embeddings or EmbeddingClient(self.settings)

    def _source_metadata(self, source_type: str, source_id: str) -> tuple[str, str | None]:
        if source_type == "tmdb_synopsis":
            synopsis = self.repo.db.get(MovieSynopsis, int(source_id))
            return (f"TMDB 简介 · {synopsis.title}", synopsis.source_url) if synopsis else ("TMDB 影片简介", None)
        return "未知资料", None

    @staticmethod
    def _split(text: str, size: int = 700, overlap: int = 100) -> list[str]:
        normalized = " ".join(text.split())
        if len(normalized) <= size:
            return [normalized]
        return [normalized[start:start + size] for start in range(0, len(normalized), size - overlap) if normalized[start:start + size]]

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if len(left) != len(right):
            return 0
        denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
        return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0

    @staticmethod
    def _excerpt(content: str, length: int = 180) -> str:
        return content if len(content) <= length else f"{content[:length]}…"
