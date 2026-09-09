from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

# 前端手动筛选支持中文类型；内部统一成 TMDB 查询所需的英文类型键。
GENRE_ALIASES = {
    "动作": "action", "冒险": "adventure", "动画": "animation", "喜剧": "comedy", "犯罪": "crime",
    "纪录": "documentary", "纪录片": "documentary", "剧情": "drama", "家庭": "family", "奇幻": "fantasy",
    "历史": "history", "恐怖": "horror", "音乐": "music", "悬疑": "mystery", "爱情": "romance",
    "科幻": "science fiction", "惊悚": "thriller", "战争": "war", "西部": "western",
}


def canonical_genre(value: str) -> str:
    """把中文类型和英文类型名称归一，便于 TMDB 查询与后端规则比较。"""
    normalized = value.strip().lower()
    return GENRE_ALIASES.get(normalized, normalized)


class WatchStatus(StrEnum):
    WANT_TO_WATCH = "want_to_watch"
    WATCHED = "watched"


class SearchMode(StrEnum):
    FULL_TEXT = "full_text"
    VECTOR = "vector"


class MovieSearchQuery(BaseModel):
    genres: list[str] = Field(default_factory=list, max_length=4)
    exclude_genres: list[str] = Field(default_factory=list, max_length=4)
    mood: str | None = Field(default=None, max_length=80)
    keyword: str | None = Field(default=None, max_length=100)
    release_year_min: int | None = Field(default=None, ge=1888, le=2100)
    release_year_max: int | None = Field(default=None, ge=1888, le=2100)
    runtime_max_minutes: int | None = Field(default=None, ge=40, le=360)
    min_vote_average: float | None = Field(default=None, ge=0, le=10)
    language: str | None = Field(default=None, pattern="^[a-z]{2}$")

    @field_validator("genres", "exclude_genres", mode="before")
    @classmethod
    def normalize_genres(cls, value: list[str] | None) -> list[str]:
        return [canonical_genre(item) for item in (value or []) if item.strip()]

    @field_validator("release_year_max")
    @classmethod
    def max_year_must_follow_min(cls, value: int | None, info) -> int | None:
        lower = info.data.get("release_year_min")
        if value is not None and lower is not None and value < lower:
            raise ValueError("release_year_max must be greater than or equal to release_year_min")
        return value


class RecommendationRequest(BaseModel):
    # 两种入口都支持：自然语言由 LLM 解析；筛选表单直接传 conditions。
    query: str | None = Field(default=None, max_length=500)
    conditions: MovieSearchQuery | None = None
    search_mode: SearchMode = SearchMode.FULL_TEXT
    # 默认一次展示 10 部；前端可继续以 limit 缩小数量，但不会超过 10。
    limit: int = Field(default=10, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value

    @model_validator(mode="after")
    def require_query_or_conditions(self) -> "RecommendationRequest":
        if self.query is None and self.conditions is None:
            raise ValueError("provide query or conditions")
        return self


class RagCitation(BaseModel):
    source_type: str
    source_name: str
    excerpt: str
    source_url: str | None = None
    similarity: float = Field(ge=0, le=1)


class Movie(BaseModel):
    tmdb_id: int
    title: str
    overview: str | None = None
    release_year: int | None = None
    runtime_minutes: int | None = None
    genres: list[str] = Field(default_factory=list)
    vote_average: float | None = None
    popularity: float | None = None
    poster_url: str | None = None
    app_url: str
    tmdb_url: str
    matched_conditions: list[str] = Field(default_factory=list)
    recommendation_reason: str | None = None
    # 缓存降级时前端可提示数据不是刚从 TMDB 刷新的。
    data_updated_at: datetime | None = None
    is_stale: bool = False
    rag_score: float | None = None
    rag_sources: list[RagCitation] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    request_id: str
    query_summary: str
    parsed_conditions: MovieSearchQuery
    summary: str
    movies: list[Movie]
    relaxation_suggestion: str | None = None


class MovieDetail(Movie):
    updated_at: datetime | None = None


class WatchlistCreate(BaseModel):
    movie_tmdb_id: int = Field(gt=0)
    status: WatchStatus = WatchStatus.WANT_TO_WATCH
    note: str | None = Field(default=None, max_length=500)


class WatchlistUpdate(BaseModel):
    status: WatchStatus | None = None
    note: str | None = Field(default=None, max_length=500)


class WatchlistItem(BaseModel):
    id: int
    movie_tmdb_id: int
    status: WatchStatus
    note: str | None
    created_at: datetime
    updated_at: datetime
    movie: Movie | None = None


class RecommendationHistoryItem(BaseModel):
    id: int
    query: str
    parsed_conditions: MovieSearchQuery
    movie_tmdb_ids: list[int]
    created_at: datetime


class ApiError(BaseModel):
    code: str
    message: str
    request_id: str


class RagStatusResponse(BaseModel):
    enabled: bool
    embedding_configured: bool
    synopsis_count: int
    chunk_count: int


class DemoSynopsisSeedResponse(BaseModel):
    imported_movies: int
    indexed_chunks: int
