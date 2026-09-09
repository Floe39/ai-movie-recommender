import asyncio

import httpx

from app.config import Settings
from app.schemas import MovieSearchQuery
from app.tmdb import TMDBClient


def test_discovery_requests_chinese_tmdb_data_and_accepts_chinese_genre():
    """不访问真实网络，验证发往 TMDB 的参数是中文展示语言且“喜剧”能映射为类型 ID。"""
    seen_params = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.update(request.url.params)
        return httpx.Response(200, json={"results": [{"id": 123}]})

    async def run():
        settings = Settings(tmdb_api_key="test-key", tmdb_base_url="https://example.test")
        async with httpx.AsyncClient(base_url=settings.tmdb_base_url, transport=httpx.MockTransport(handler)) as http:
            return await TMDBClient(settings, http).discover(MovieSearchQuery(genres=["喜剧"]))

    assert asyncio.run(run()) == [123]
    assert seen_params["language"] == "zh-CN"
    assert seen_params["with_genres"] == "35"
    assert 1 <= int(seen_params["page"]) <= 5
