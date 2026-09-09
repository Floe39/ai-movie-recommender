from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 由源码文件的位置推导，而不是依赖用户执行命令时所在的工作目录。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "movie_recommender.db"


class Settings(BaseSettings):
    # 无论从哪里启动 python，始终读取项目根目录的 .env。
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    llm_provider: str = Field(default="auto", pattern="^(auto|deepseek|dashscope)$")
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    dashscope_api_key: str | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_model: str = "qwen-plus"
    # RAG 向量化使用百炼的 OpenAI 兼容 Embedding 接口，与对话模型配置分开管理。
    dashscope_embedding_model: str = "text-embedding-v4"
    embedding_dimensions: int = Field(default=1024, ge=64, le=2048)
    rag_enabled: bool = True
    rag_top_k: int = Field(default=3, ge=1, le=10)
    llm_temperature: float = Field(default=0, ge=0, le=2)
    llm_timeout_seconds: int = Field(default=30, ge=1, le=120)
    tmdb_api_key: str | None = None
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base_url: str = "https://image.tmdb.org/t/p/w500"
    # TMDB 返回标题、简介和类型时优先使用中文翻译；没有中文译文时 API 会保留原始资料。
    tmdb_language: str = "zh-CN"
    database_url: str = f"sqlite:///{DEFAULT_DATABASE_PATH}"
    cache_ttl_hours: int = Field(default=168, ge=1)

    @model_validator(mode="after")
    def verify_selected_provider_has_a_key(self) -> "Settings":
        if self.llm_provider == "deepseek" and not self.deepseek_api_key:
            raise ValueError("LLM_PROVIDER=deepseek requires DEEPSEEK_API_KEY")
        if self.llm_provider == "dashscope" and not self.dashscope_api_key:
            raise ValueError("LLM_PROVIDER=dashscope requires DASHSCOPE_API_KEY")
        # 兼容 .env.example 的相对 SQLite URL，同时使它相对项目根目录而非当前命令目录。
        if self.database_url.startswith("sqlite:///") and self.database_url != "sqlite:///:memory:":
            path_value = self.database_url.removeprefix("sqlite:///")
            if path_value and not path_value.startswith("/"):
                self.database_url = f"sqlite:///{PROJECT_ROOT / path_value}"
        return self

    def active_llm(self) -> tuple[str, str, str, str]:
        if self.llm_provider == "deepseek" or (self.llm_provider == "auto" and self.deepseek_api_key):
            if self.deepseek_api_key:
                return "deepseek", self.deepseek_api_key, self.deepseek_base_url, self.deepseek_model
        if self.llm_provider == "dashscope" or (self.llm_provider == "auto" and self.dashscope_api_key):
            if self.dashscope_api_key:
                return "dashscope", self.dashscope_api_key, self.dashscope_base_url, self.dashscope_model
        raise ValueError("Configure DEEPSEEK_API_KEY or DASHSCOPE_API_KEY before requesting recommendations")


@lru_cache
def get_settings() -> Settings:
    return Settings()
