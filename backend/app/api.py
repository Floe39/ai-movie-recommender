import json
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .database import create_database_schema, get_db
from .embeddings import EmbeddingError
from .llm import LLMClient, LLMError
from .repository import Repository
from .rag import RAGService
from .schemas import (ApiError, Movie, MovieDetail, RecommendationHistoryItem, RecommendationRequest,
                      DemoSynopsisSeedResponse, RecommendationResponse, RagStatusResponse, WatchStatus, WatchlistCreate,
                      WatchlistItem, WatchlistUpdate)
from .service import RecommendationService
from .tmdb import TMDBClient, TMDBError


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_database_schema()
    yield


app = FastAPI(title="AI Movie Recommender API", version="0.1.0", lifespan=lifespan)


def error_response(code: str, message: str, request_id: str | None = None, http_status: int = 400) -> JSONResponse:
    return JSONResponse(status_code=http_status, content=ApiError(code=code, message=message, request_id=request_id or str(uuid.uuid4())).model_dump())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    message = exc.errors()[0]["msg"] if exc.errors() else "Invalid request"
    return error_response("VALIDATION_ERROR", message, http_status=422)


@app.exception_handler(LLMError)
async def llm_error_handler(_: Request, __: LLMError):
    return error_response("LLM_UNAVAILABLE", "模型服务暂时不可用，请稍后重试。", http_status=503)


@app.exception_handler(TMDBError)
async def tmdb_error_handler(_: Request, __: TMDBError):
    return error_response("MOVIE_DATA_UNAVAILABLE", "电影数据服务暂时不可用，请稍后重试。", http_status=503)


@app.exception_handler(EmbeddingError)
async def embedding_error_handler(_: Request, __: EmbeddingError):
    return error_response("RAG_UNAVAILABLE", "资料库向量服务暂时不可用，请检查百炼 Embedding 配置。", http_status=503)


def get_service(db: Session = Depends(get_db)) -> RecommendationService:
    # 配置缺少 Key 时也转成统一的 LLM 服务错误，而不是暴露 500。
    try:
        return RecommendationService(db, LLMClient(), TMDBClient())
    except ValueError as exc:
        raise LLMError("LLM configuration is incomplete") from exc


def watchlist_response(item, movie: Movie | None = None) -> WatchlistItem:
    return WatchlistItem(id=item.id, movie_tmdb_id=item.movie_tmdb_id, status=item.status, note=item.note,
                         created_at=item.created_at, updated_at=item.updated_at, movie=movie)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/recommendations", response_model=RecommendationResponse)
async def create_recommendation(payload: RecommendationRequest, service: RecommendationService = Depends(get_service)):
    try:
        return await service.recommend(payload.query, payload.limit, payload.conditions, payload.search_mode)
    finally:
        await service.tmdb.close()


@app.get("/api/movies/today", response_model=list[Movie])
async def get_today_movies(limit: int = 5, service: RecommendationService = Depends(get_service)):
    if not 4 <= limit <= 5:
        raise HTTPException(status_code=422, detail="limit must be between 4 and 5")
    try:
        return await service.today_recommendations(limit)
    finally:
        await service.tmdb.close()


@app.get("/api/movies/{tmdb_id}", response_model=MovieDetail)
async def get_movie(tmdb_id: int, service: RecommendationService = Depends(get_service)):
    try:
        movie = await service.get_movie(tmdb_id)
        if movie is None:
            raise HTTPException(status_code=404, detail="Movie not found")
        return MovieDetail(**movie.model_dump())
    finally:
        await service.tmdb.close()


@app.get("/api/watchlist", response_model=list[WatchlistItem])
async def list_watchlist(status_filter: WatchStatus | None = None, db: Session = Depends(get_db)):
    repo = Repository(db)
    return [watchlist_response(item) for item in repo.list_watchlist(status_filter)]


@app.post("/api/watchlist", response_model=WatchlistItem, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(payload: WatchlistCreate, db: Session = Depends(get_db)):
    return watchlist_response(Repository(db).save_watchlist_item(payload.movie_tmdb_id, payload.status, payload.note))


@app.patch("/api/watchlist/{tmdb_id}", response_model=WatchlistItem)
async def update_watchlist(tmdb_id: int, payload: WatchlistUpdate, db: Session = Depends(get_db)):
    repo = Repository(db)
    item = repo.get_watchlist_item(tmdb_id)
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return watchlist_response(repo.save_watchlist_item(tmdb_id, payload.status or WatchStatus(item.status), payload.note if payload.note is not None else item.note))


@app.delete("/api/watchlist/{tmdb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(tmdb_id: int, db: Session = Depends(get_db)) -> Response:
    if not Repository(db).delete_watchlist_item(tmdb_id):
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/recommendations/history", response_model=list[RecommendationHistoryItem])
async def list_recommendation_history(db: Session = Depends(get_db)):
    return [RecommendationHistoryItem(id=item.id, query=item.query,
                                      parsed_conditions=json.loads(item.parsed_conditions_json),
                                      movie_tmdb_ids=json.loads(item.movie_tmdb_ids_json), created_at=item.created_at)
            for item in Repository(db).list_history()]


@app.get("/api/rag/status", response_model=RagStatusResponse)
async def get_rag_status(db: Session = Depends(get_db)):
    enabled, configured, synopses, chunks = RAGService(db).status()
    return RagStatusResponse(enabled=enabled, embedding_configured=configured, synopsis_count=synopses,
                             chunk_count=chunks)


@app.post("/api/rag/demo-synopses/seed", response_model=DemoSynopsisSeedResponse)
async def seed_demo_synopses(db: Session = Depends(get_db)):
    """从 TMDB 导入少量真实影片简介，供故事描述检索演示。"""
    tmdb = TMDBClient()
    try:
        imported_movies, indexed_chunks = await RAGService(db).seed_demo_synopses(tmdb)
        return DemoSynopsisSeedResponse(imported_movies=imported_movies, indexed_chunks=indexed_chunks)
    finally:
        await tmdb.close()

