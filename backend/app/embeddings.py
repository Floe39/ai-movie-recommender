from openai import APIError, AsyncOpenAI

from .config import Settings, get_settings


class EmbeddingError(RuntimeError):
    pass


class EmbeddingClient:
    """通过百炼 OpenAI 兼容接口生成 RAG 所需的文本向量。"""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if not self.settings.dashscope_api_key:
            raise EmbeddingError("RAG requires DASHSCOPE_API_KEY")
        self.client = AsyncOpenAI(api_key=self.settings.dashscope_api_key,
                                  base_url=self.settings.dashscope_base_url,
                                  timeout=self.settings.llm_timeout_seconds,
                                  max_retries=1)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self.client.embeddings.create(
                model=self.settings.dashscope_embedding_model,
                input=texts,
                dimensions=self.settings.embedding_dimensions,
                encoding_format="float",
            )
            return [item.embedding for item in response.data]
        except APIError as exc:
            raise EmbeddingError("Embedding service is unavailable") from exc
