from collections.abc import Iterable
import random

import httpx

from .config import Settings, get_settings
from .schemas import Movie, MovieSearchQuery, canonical_genre


class TMDBError(RuntimeError):
    pass


GENRE_IDS = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35, "crime": 80,
    "documentary": 99, "drama": 18, "family": 10751, "fantasy": 14, "history": 36,
    "horror": 27, "music": 10402, "mystery": 9648, "romance": 10749, "science fiction": 878,
    "thriller": 53, "war": 10752, "western": 37,
}


class TMDBClient:
    def __init__(self, settings: Settings | None = None, http_client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings()
        self.http = http_client or httpx.AsyncClient(base_url=self.settings.tmdb_base_url, timeout=15)
        self.owns_client = http_client is None

    async def close(self) -> None:
        if self.owns_client:
            await self.http.aclose()

    async def discover(self, conditions: MovieSearchQuery, page: int | None = None) -> list[int]:
        """从 TMDB 取候选 ID；硬条件仍必须在详情数据上由业务层复核。"""
        if not self.settings.tmdb_api_key:
            raise TMDBError("TMDB_API_KEY is not configured")
        params: dict[str, str | int | float] = {
            "api_key": self.settings.tmdb_api_key,
            "language": self.settings.tmdb_language,
            "include_adult": "false",
            "sort_by": "popularity.desc",
            # 未指定时从前五页热门候选中随机取一页；“今日推荐”会传入固定页。
            "page": page if page is not None else random.randint(1, 5),
        }
        if conditions.language:
            params["with_original_language"] = conditions.language
        if conditions.release_year_min:
            params["primary_release_date.gte"] = f"{conditions.release_year_min}-01-01"
        if conditions.release_year_max:
            params["primary_release_date.lte"] = f"{conditions.release_year_max}-12-31"
        if conditions.min_vote_average:
            params["vote_average.gte"] = conditions.min_vote_average
            params["vote_count.gte"] = 20
        include_ids = self._genre_ids(conditions.genres)
        exclude_ids = self._genre_ids(conditions.exclude_genres)
        if include_ids:
            params["with_genres"] = ",".join(map(str, include_ids))
        if exclude_ids:
            params["without_genres"] = ",".join(map(str, exclude_ids))
        try:
            # TMDB discover 不能用自由文本片名搜索；有关键词时切到 search 接口。
            endpoint = "/search/movie" if conditions.keyword else "/discover/movie"
            if conditions.keyword:
                params["query"] = conditions.keyword
                params.pop("with_genres", None)
                params.pop("without_genres", None)
            response = await self.http.get(endpoint, params=params)
            response.raise_for_status()
            return [item["id"] for item in response.json().get("results", []) if isinstance(item.get("id"), int)]
        except httpx.HTTPError as exc:
            raise TMDBError("TMDB movie discovery failed") from exc

    async def movie_detail(self, tmdb_id: int) -> tuple[Movie, str | None]:
        """详情接口是时长等硬条件的可信来源，搜索结果本身不能直接使用。"""
        if not self.settings.tmdb_api_key:
            raise TMDBError("TMDB_API_KEY is not configured")
        try:
            response = await self.http.get(f"/movie/{tmdb_id}", params={"api_key": self.settings.tmdb_api_key, "language": self.settings.tmdb_language})
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise TMDBError("TMDB movie detail lookup failed") from exc
        date = data.get("release_date") or ""
        poster_path = data.get("poster_path")
        return Movie(
            tmdb_id=data["id"], title=data.get("title") or data.get("original_title") or "Untitled",
            overview=data.get("overview") or None, release_year=int(date[:4]) if date[:4].isdigit() else None,
            runtime_minutes=data.get("runtime") or None, genres=[genre["name"] for genre in data.get("genres", [])],
            vote_average=data.get("vote_average"), popularity=data.get("popularity"),
            poster_url=f"{self.settings.tmdb_image_base_url}{poster_path}" if poster_path else None,
            app_url=f"/movies/{data['id']}", tmdb_url=f"https://www.themoviedb.org/movie/{data['id']}",
        ), poster_path

    @staticmethod
    def _genre_ids(genres: Iterable[str]) -> list[int]:
        return [GENRE_IDS[canonical_genre(item)] for item in genres if canonical_genre(item) in GENRE_IDS]
