import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Base
from app.rag import RAGService
from app.schemas import Movie, MovieSearchQuery, SearchMode
from app.service import RecommendationService


class FakeLLM:
    async def parse_conditions(self, _query: str) -> MovieSearchQuery:
        return MovieSearchQuery(genres=["comedy"], runtime_max_minutes=120)

    async def write_reasons(self, _query: str, movies: list[Movie]) -> dict[int, str]:
        return {movie.tmdb_id: "时长和喜剧类型符合这次需求。" for movie in movies}


class FakeTMDB:
    def __init__(self):
        self.discover_calls = 0

    async def discover(self, _conditions: MovieSearchQuery, page: int | None = None) -> list[int]:
        self.discover_calls += 1
        return [1, 2]

    async def movie_detail(self, tmdb_id: int) -> tuple[Movie, str | None]:
        movies = {
            1: Movie(tmdb_id=1, title="Short Comedy", runtime_minutes=100, release_year=2024, genres=["Comedy"], vote_average=7.5, popularity=50, app_url="/movies/1", tmdb_url="https://www.themoviedb.org/movie/1"),
            2: Movie(tmdb_id=2, title="Long Comedy", runtime_minutes=140, release_year=2024, genres=["Comedy"], vote_average=8, popularity=80, app_url="/movies/2", tmdb_url="https://www.themoviedb.org/movie/2"),
        }
        return movies[tmdb_id], None

    async def close(self) -> None:
        return None


class ConstantEmbeddings:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def test_recommendation_filters_hard_constraints_and_saves_history():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    settings = Settings(database_url="sqlite:///:memory:")
    with Session(engine) as db:
        service = RecommendationService(db, FakeLLM(), FakeTMDB(), settings)
        response = asyncio.run(service.recommend("两小时以内的轻松喜剧", 5))

        assert [movie.tmdb_id for movie in response.movies] == [1]
        assert response.movies[0].recommendation_reason == "时长和喜剧类型符合这次需求。"
        assert service.repo.list_history()[0].movie_tmdb_ids_json == "[1]"


def test_manual_conditions_do_not_require_llm_parsing():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tmdb = FakeTMDB()
        service = RecommendationService(db, FakeLLM(), tmdb, Settings(database_url="sqlite:///:memory:"))
        response = asyncio.run(service.recommend(None, 5, MovieSearchQuery(genres=["comedy"], runtime_max_minutes=120)))

        assert response.query_summary == "按手动筛选条件推荐"
        assert [movie.tmdb_id for movie in response.movies] == [1]


def test_recommendation_request_defaults_to_ten_results():
    from app.schemas import RecommendationRequest

    assert RecommendationRequest(query="周末轻松电影").limit == 10


def test_today_recommendations_use_high_score_tmdb_candidates():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        tmdb = FakeTMDB()
        service = RecommendationService(db, FakeLLM(), tmdb, Settings(database_url="sqlite:///:memory:"))
        movies = asyncio.run(service.today_recommendations(5))
        repeated_movies = asyncio.run(service.today_recommendations(5))

        assert {movie.tmdb_id for movie in movies} == {1, 2}
        assert all((movie.vote_average or 0) >= 7 for movie in movies)
        assert [movie.tmdb_id for movie in movies] == [movie.tmdb_id for movie in repeated_movies]
        assert tmdb.discover_calls == 1


def test_vector_mode_uses_seeded_movie_synopsis_embeddings():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    settings = Settings(database_url="sqlite:///:memory:", dashscope_api_key="test-key")
    with Session(engine) as db:
        rag = RAGService(db, embeddings=ConstantEmbeddings(), settings=settings)
        rag.repo.upsert_synopsis(1, "小红帽", "一个小女孩在森林里遇到狼的故事。", "https://example.test/movie/1")
        asyncio.run(rag._index("tmdb_synopsis", "1", "一个小女孩在森林里遇到狼的故事。", 1))
        response = asyncio.run(RecommendationService(db, FakeLLM(), FakeTMDB(), settings, rag).recommend(
            "一个小女孩和一匹狼的故事", 10, search_mode=SearchMode.VECTOR))

        # 向量模式只返回资料库命中的影片，不用 TMDB 候选补足数量。
        assert [movie.tmdb_id for movie in response.movies] == [1]
        assert response.movies[0].rag_sources[0].source_name.startswith("TMDB 简介")
