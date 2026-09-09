import json

from openai import APIError, AsyncOpenAI

from .config import Settings, get_settings
from .schemas import Movie, MovieSearchQuery


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Uses OpenAI-compatible endpoints exposed by DeepSeek and DashScope."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.provider, api_key, base_url, self.model = self.settings.active_llm()
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=self.settings.llm_timeout_seconds, max_retries=1)

    async def parse_conditions(self, query: str) -> MovieSearchQuery:
        prompt = """Extract movie search filters from the user request. Return JSON only, using exactly these keys:
genres (array), exclude_genres (array), mood (string|null), keyword (string|null), release_year_min (integer|null), release_year_max (integer|null), runtime_max_minutes (integer|null), min_vote_average (number|null), language (two-letter ISO 639-1 code|null).
Do not invent constraints. Genres should be lowercase English genre names when clear."""
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": query}],
            )
            return MovieSearchQuery.model_validate(json.loads(completion.choices[0].message.content or "{}"))
        except (APIError, ValueError, json.JSONDecodeError) as exc:
            raise LLMError("Unable to parse movie preferences") from exc

    async def write_reasons(self, query: str, movies: list[Movie]) -> dict[int, str]:
        if not movies:
            return {}
        candidates = [movie.model_dump(include={"tmdb_id", "title", "overview", "release_year", "runtime_minutes", "genres", "vote_average", "rag_sources"}) for movie in movies]
        prompt = """Write one brief Chinese recommendation reason for each supplied movie. Use only the supplied TMDB facts and RAG source excerpts; do not claim unprovided awards, plot details, cast, or availability. If an RAG source excerpt exists, you may mention that the retrieved synopsis or note matches the request, without treating it as a verified movie fact. Return JSON only as {\"reasons\": [{\"tmdb_id\": number, \"reason\": string}]}.
User request:"""
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                temperature=self.settings.llm_temperature,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": json.dumps({"query": query, "candidates": candidates}, ensure_ascii=False)}],
            )
            payload = json.loads(completion.choices[0].message.content or "{}")
            allowed_ids = {movie.tmdb_id for movie in movies}
            return {item["tmdb_id"]: item["reason"] for item in payload.get("reasons", []) if item.get("tmdb_id") in allowed_ids and isinstance(item.get("reason"), str)}
        except (APIError, ValueError, json.JSONDecodeError, KeyError) as exc:
            raise LLMError("Unable to generate recommendation reasons") from exc
