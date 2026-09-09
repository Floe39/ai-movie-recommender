from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MovieCache(Base):
    """TMDB 详情缓存：只保存展示和规则过滤所需的可验证字段。"""
    __tablename__ = "movies"

    tmdb_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    genres_json: Mapped[str] = mapped_column(Text, default="[]")
    vote_average: Mapped[float | None] = mapped_column(nullable=True)
    popularity: Mapped[float | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class WatchlistItemModel(Base):
    """匿名用户的片单；唯一约束避免同一电影重复加入。"""
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("movie_tmdb_id", name="uq_watchlist_movie_tmdb_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_tmdb_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class RecommendationHistory(Base):
    """可回放的业务结果，不等同于聊天上下文。"""
    __tablename__ = "recommendation_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(Text)
    parsed_conditions_json: Mapped[str] = mapped_column(Text)
    movie_tmdb_ids_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DailyRecommendation(Base):
    """每日推荐缓存：同一天首页只读取已生成的电影 ID，不重复请求 TMDB。"""
    __tablename__ = "daily_recommendations"

    day: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD
    movie_tmdb_ids_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RagChunk(Base):
    """可检索的文本切块与向量。小规模作品集用 SQLite JSON 持久化向量即可。"""
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(30), index=True)  # 当前固定为 tmdb_synopsis
    source_id: Mapped[str] = mapped_column(String(120), index=True)
    movie_tmdb_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    embedding_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MovieSynopsis(Base):
    """RAG 演示语料：从 TMDB 读取的少量真实影片简介。"""
    __tablename__ = "movie_synopses"

    tmdb_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    overview: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
