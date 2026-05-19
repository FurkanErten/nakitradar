from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NakitRadar AI"
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # LLM configuration. Backend only; never expose keys to frontend.
    # auto: Ollama local -> Gemini -> OpenAI -> deterministic local CFO fallback
    # ollama: only local Ollama -> deterministic local fallback
    # gemini: only Gemini -> deterministic local fallback
    # openai: only OpenAI -> deterministic local fallback
    # disabled/local: deterministic local CFO only
    llm_provider: str = "auto"

    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    openai_timeout_seconds: float = 25

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 25

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = 60

    ai_max_context_products: int = 8
    ai_max_context_actions: int = 8

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def provider_mode(self) -> str:
        return (self.llm_provider or "disabled").strip().lower()

    @property
    def ai_enabled(self) -> bool:
        return self.provider_mode != "disabled"

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key) and self.provider_mode in {"auto", "openai"}

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key) and self.provider_mode in {"auto", "gemini"}

    @property
    def ollama_enabled(self) -> bool:
        return self.provider_mode in {"auto", "ollama"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
