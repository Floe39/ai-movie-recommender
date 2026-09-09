import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DailyRecommendation, MovieCache, MovieSynopsis, RagChunk, RecommendationHistory, WatchlistItemModel
from .schemas import Movie, MovieSearchQuery, WatchStatus


class Repository:
    def __init__(self, db: Session):
        self.db = db

    def get_cached_movie(self, tmdb_id: int, ttl_hours: int) -> MovieCache | None:
        """仅返回仍在 TTL 内的缓存，用于正常请求路径。"""
        movie = self.get_movie_cache(tmdb_id)
        if not movie:
            return None
        updated_at = movie.updated_at.replace(tzinfo=timezone.utc) if movie.updated_at.tzinfo is None else movie.updated_at
        if updated_at < datetime.now(timezone.utc) - timedelta(hours=ttl_hours):
            return None
        return movie

    def get_movie_cache(self, tmdb_id: int) -> MovieCache | None:
        """返回任何缓存版本，TMDB 故障时可作为只读降级数据。"""
        return self.db.get(MovieCache, tmdb_id)

    def upsert_movie(self, movie: Movie, poster_path: str | None = None) -> MovieCache:
        cached = self.db.get(MovieCache, movie.tmdb_id)
        if cached is None:
            cached = MovieCache(tmdb_id=movie.tmdb_id, title=movie.title)
            self.db.add(cached)
        cached.title = movie.title
        cached.overview = movie.overview
        cached.poster_path = poster_path
        cached.release_year = movie.release_year
        cached.runtime_minutes = movie.runtime_minutes
        cached.genres_json = json.dumps(movie.genres, ensure_ascii=False)
        cached.vote_average = movie.vote_average
        cached.popularity = movie.popularity
        self.db.flush()
        return cached

    def save_history(self, query: str, conditions: MovieSearchQuery, tmdb_ids: list[int]) -> RecommendationHistory:
        item = RecommendationHistory(
            query=query,
            parsed_conditions_json=conditions.model_dump_json(),
            movie_tmdb_ids_json=json.dumps(tmdb_ids),
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_history(self) -> list[RecommendationHistory]:
        return list(self.db.scalars(select(RecommendationHistory).order_by(RecommendationHistory.created_at.desc())))

    def get_daily_recommendation(self, day: str) -> DailyRecommendation | None:
        return self.db.get(DailyRecommendation, day)

    def save_daily_recommendation(self, day: str, tmdb_ids: list[int]) -> DailyRecommendation:
        item = DailyRecommendation(day=day, movie_tmdb_ids_json=json.dumps(tmdb_ids))
        self.db.merge(item)
        self.db.commit()
        return self.db.get(DailyRecommendation, day)

    def list_watchlist(self, status: WatchStatus | None = None) -> list[WatchlistItemModel]:
        query = select(WatchlistItemModel).order_by(WatchlistItemModel.updated_at.desc())
        if status:
            query = query.where(WatchlistItemModel.status == status.value)
        return list(self.db.scalars(query))

    def get_watchlist_item(self, movie_tmdb_id: int) -> WatchlistItemModel | None:
        return self.db.scalar(select(WatchlistItemModel).where(WatchlistItemModel.movie_tmdb_id == movie_tmdb_id))

    def save_watchlist_item(self, movie_tmdb_id: int, status: WatchStatus, note: str | None) -> WatchlistItemModel:
        item = self.get_watchlist_item(movie_tmdb_id)
        if item is None:
            item = WatchlistItemModel(movie_tmdb_id=movie_tmdb_id, status=status.value, note=note)
            self.db.add(item)
        else:
            item.status, item.note = status.value, note
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_watchlist_item(self, movie_tmdb_id: int) -> bool:
        item = self.get_watchlist_item(movie_tmdb_id)
        if item is None:
            return False
        self.db.delete(item)
        self.db.commit()
        return True

    def replace_chunks(self, source_type: str, source_id: str, chunks: list[tuple[str, list[float], int | None]]) -> int:
        """同一资料重新同步时覆盖旧向量，避免重复召回。"""
        self.db.query(RagChunk).filter(RagChunk.source_type == source_type, RagChunk.source_id == source_id).delete()
        self.db.add_all([RagChunk(source_type=source_type, source_id=source_id, movie_tmdb_id=movie_id,
                                  content=content, embedding_json=json.dumps(embedding))
                         for content, embedding, movie_id in chunks])
        self.db.commit()
        return len(chunks)

    def list_chunks(self, movie_ids: list[int] | None = None) -> list[RagChunk]:
        query = select(RagChunk)
        if movie_ids:
            query = query.where(RagChunk.movie_tmdb_id.in_(movie_ids))
        return list(self.db.scalars(query))

    def has_movie_chunks(self, movie_tmdb_id: int) -> bool:
        return self.db.scalar(select(RagChunk.id).where(RagChunk.movie_tmdb_id == movie_tmdb_id).limit(1)) is not None

    def rag_counts(self) -> tuple[int, int]:
        """返回已导入的演示简介与向量片段数。"""
        return (len(list(self.db.scalars(select(MovieSynopsis.tmdb_id)))),
                len(list(self.db.scalars(select(RagChunk.id)))))

    def upsert_synopsis(self, tmdb_id: int, title: str, overview: str, source_url: str) -> MovieSynopsis:
        synopsis = self.db.get(MovieSynopsis, tmdb_id)
        if synopsis is None:
            synopsis = MovieSynopsis(tmdb_id=tmdb_id, title=title, overview=overview, source_url=source_url)
            self.db.add(synopsis)
        else:
            synopsis.title, synopsis.overview, synopsis.source_url = title, overview, source_url
        self.db.flush()
        return synopsis

    def list_synopses(self) -> list[MovieSynopsis]:
        return list(self.db.scalars(select(MovieSynopsis)))
