import json
import random
import uuid
from datetime import date, timezone

from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .llm import LLMClient
from .rag import RAGService
from .repository import Repository
from .schemas import Movie, MovieSearchQuery, RecommendationResponse, SearchMode, canonical_genre
from .tmdb import TMDBClient
from .tmdb import TMDBError


class RecommendationService:
    def __init__(self, db: Session, llm: LLMClient, tmdb: TMDBClient, settings: Settings | None = None,
                 rag: RAGService | None = None):
        self.repo = Repository(db)
        self.llm = llm
        self.tmdb = tmdb
        self.settings = settings or get_settings()
        self.rag = rag or RAGService(db, settings=self.settings)

    async def recommend(self, query: str | None, limit: int, explicit_conditions: MovieSearchQuery | None = None,
                        search_mode: SearchMode = SearchMode.FULL_TEXT) -> RecommendationResponse:
        # 表单筛选无需再次调用模型；自然语言请求才进入 LLM 解析。
        conditions = explicit_conditions or await self.llm.parse_conditions(query or "")
        query_summary = query or "按手动筛选条件推荐"
        citations: dict[int, list] = {}
        rag_matched = False
        if search_mode == SearchMode.VECTOR:
            # 故事模式只从已向量化的影片简介中召回，不用 TMDB 候选补足数量。
            citations = await self.rag.search_synopses_vector(query_summary)
            candidate_ids = self._rag_ranked_ids(citations)
            rag_matched = bool(citations)
        else:
            # 条件模式不使用 RAG：LLM 只提取类型、时长、年份、评分等条件，再由 TMDB 真实数据筛选。
            candidate_ids = await self.tmdb.discover(conditions)
        movies: list[Movie] = []
        for tmdb_id in candidate_ids[:20]:
            movie = await self._get_movie(tmdb_id)
            if movie and self._matches_hard_conditions(movie, conditions):
                movie.matched_conditions = self._matched_conditions(movie, conditions)
                movie.rag_sources = citations.get(movie.tmdb_id, [])
                movie.rag_score = movie.rag_sources[0].similarity if movie.rag_sources else 0
                movies.append(movie)
        movies.sort(key=lambda movie: self._ranking_score(movie, conditions), reverse=True)
        if rag_matched:
            # RAG 模式优先依据命中资料数量与相似度，不随机掺入其他影片。
            movies.sort(key=lambda movie: (len(movie.rag_sources), movie.rag_score or 0), reverse=True)
            selected = movies[:limit]
        else:
            # 普通 TMDB 条件检索仍保留高质量候选池随机化，避免同一需求总是同一片单。
            high_quality_pool = movies[: max(limit, min(len(movies), limit * 3))]
            selected = random.sample(high_quality_pool, k=min(limit, len(high_quality_pool)))
            selected.sort(key=lambda movie: self._ranking_score(movie, conditions), reverse=True)
        reasons = await self.llm.write_reasons(query_summary, selected)
        for movie in selected:
            movie.recommendation_reason = reasons.get(movie.tmdb_id, "符合你设定的筛选条件，可在详情页查看完整信息。")
        self.repo.save_history(query_summary, conditions, [movie.tmdb_id for movie in selected])
        return RecommendationResponse(
            request_id=str(uuid.uuid4()), query_summary=query_summary, parsed_conditions=conditions,
            summary=f"基于已验证的 TMDB 数据筛选出 {len(selected)} 部影片。" if selected else "没有找到满足当前条件的影片。",
            movies=selected,
            relaxation_suggestion=None if selected else "可以尝试放宽年份、时长或类型条件后再试。",
        )

    async def get_movie(self, tmdb_id: int) -> Movie | None:
        return await self._get_movie(tmdb_id)

    async def today_recommendations(self, limit: int = 5) -> list[Movie]:
        """每天生成固定的高分片单，不经过 LLM 或 RAG。"""
        conditions = MovieSearchQuery(min_vote_average=7.0)
        day = date.today()
        # 当天已有结果时只从 SQLite 读取，不再请求 TMDB。
        cached_daily = self.repo.get_daily_recommendation(day.isoformat())
        if cached_daily:
            tmdb_ids = json.loads(cached_daily.movie_tmdb_ids_json)
            cached_movies = [self.repo.get_movie_cache(tmdb_id) for tmdb_id in tmdb_ids]
            if all(cached_movies):
                return [self._movie_from_cache(movie) for movie in cached_movies]

        # 同一天使用相同页码和随机种子；进入下一天才会更换片单。
        period_key = day.toordinal()
        candidates: list[Movie] = []
        for tmdb_id in (await self.tmdb.discover(conditions, page=period_key % 5 + 1))[:20]:
            movie = await self._get_movie(tmdb_id)
            if movie and self._matches_hard_conditions(movie, conditions):
                candidates.append(movie)
        # 固定种子只影响当天的选片，不会改变其他推荐请求的随机性。
        candidates.sort(key=lambda movie: ((movie.vote_average or 0), (movie.popularity or 0)), reverse=True)
        pool = candidates[:max(limit, min(len(candidates), limit * 3))]
        selected = random.Random(period_key).sample(pool, k=min(limit, len(pool)))
        self.repo.save_daily_recommendation(day.isoformat(), [movie.tmdb_id for movie in selected])
        return selected

    async def _get_movie(self, tmdb_id: int) -> Movie | None:
        cached = self.repo.get_cached_movie(tmdb_id, self.settings.cache_ttl_hours)
        if cached:
            return self._movie_from_cache(cached)
        # 过期缓存不能正常命中，但可在 TMDB 不可用时保障详情页和推荐不完全失效。
        stale_cache = self.repo.get_movie_cache(tmdb_id)
        try:
            movie, poster_path = await self.tmdb.movie_detail(tmdb_id)
        except TMDBError:
            if stale_cache:
                return self._movie_from_cache(stale_cache, is_stale=True)
            raise
        self.repo.upsert_movie(movie, poster_path)
        self.repo.db.commit()
        return movie

    def _movie_from_cache(self, cached, is_stale: bool = False) -> Movie:
        updated_at = cached.updated_at.replace(tzinfo=timezone.utc) if cached.updated_at.tzinfo is None else cached.updated_at
        return Movie(
            tmdb_id=cached.tmdb_id, title=cached.title, overview=cached.overview, release_year=cached.release_year,
            runtime_minutes=cached.runtime_minutes, genres=json.loads(cached.genres_json), vote_average=cached.vote_average,
            popularity=cached.popularity, poster_url=f"{self.settings.tmdb_image_base_url}{cached.poster_path}" if cached.poster_path else None,
            app_url=f"/movies/{cached.tmdb_id}", tmdb_url=f"https://www.themoviedb.org/movie/{cached.tmdb_id}",
            data_updated_at=updated_at, is_stale=is_stale,
        )

    @staticmethod
    def _matches_hard_conditions(movie: Movie, conditions: MovieSearchQuery) -> bool:
        movie_genres = {canonical_genre(genre) for genre in movie.genres}
        if conditions.runtime_max_minutes is not None and (movie.runtime_minutes is None or movie.runtime_minutes > conditions.runtime_max_minutes):
            return False
        if conditions.release_year_min is not None and (movie.release_year is None or movie.release_year < conditions.release_year_min):
            return False
        if conditions.release_year_max is not None and (movie.release_year is None or movie.release_year > conditions.release_year_max):
            return False
        if conditions.min_vote_average is not None and (movie.vote_average is None or movie.vote_average < conditions.min_vote_average):
            return False
        if conditions.genres and not {canonical_genre(genre) for genre in conditions.genres}.intersection(movie_genres):
            return False
        if {canonical_genre(genre) for genre in conditions.exclude_genres}.intersection(movie_genres):
            return False
        return True

    @staticmethod
    def _matched_conditions(movie: Movie, conditions: MovieSearchQuery) -> list[str]:
        matched: list[str] = []
        if conditions.runtime_max_minutes is not None:
            matched.append(f"时长不超过 {conditions.runtime_max_minutes} 分钟")
        if conditions.release_year_min is not None or conditions.release_year_max is not None:
            matched.append("上映年份符合要求")
        if conditions.genres:
            matched.append("类型符合要求")
        if conditions.exclude_genres:
            matched.append("已排除指定类型")
        if conditions.min_vote_average is not None:
            matched.append(f"评分不低于 {conditions.min_vote_average}")
        return matched

    @staticmethod
    def _score(movie: Movie, conditions: MovieSearchQuery) -> float:
        matching = len(RecommendationService._matched_conditions(movie, conditions))
        total_conditions = sum([bool(conditions.runtime_max_minutes), bool(conditions.release_year_min or conditions.release_year_max), bool(conditions.genres), bool(conditions.exclude_genres), bool(conditions.min_vote_average)])
        match_score = matching / total_conditions if total_conditions else 0.6
        rating_score = (movie.vote_average or 0) / 10
        popularity_score = min((movie.popularity or 0) / 1000, 1)
        return match_score * 0.6 + rating_score * 0.25 + popularity_score * 0.15

    @staticmethod
    def _ranking_score(movie: Movie, conditions: MovieSearchQuery) -> float:
        """RAG 只提供附加语义信号，不能覆盖 TMDB 硬条件与基础质量排序。"""
        return RecommendationService._score(movie, conditions) * 0.8 + (movie.rag_score or 0) * 0.2

    @staticmethod
    def _rag_ranked_ids(citations: dict[int, list]) -> list[int]:
        """资料命中越多越靠前；命中数相同时再比较最高语义/词语相似度。"""
        return sorted(citations, key=lambda movie_id: (len(citations[movie_id]), citations[movie_id][0].similarity), reverse=True)
