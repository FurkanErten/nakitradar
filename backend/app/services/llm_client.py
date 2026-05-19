from __future__ import annotations

from app.core.config import get_settings


class LLMClient:
    """Opsiyonel LLM adaptörü.

    Hackathon demosu internet/API anahtarına bağlı kalmasın diye varsayılan kapalıdır.
    Gerçek ürünleşmede burada OpenAI, Vertex AI veya yerel model adaptörü kullanılabilir.
    """

    def __init__(self):
        self.settings = get_settings()

    def enabled(self) -> bool:
        return bool(self.settings.openai_api_key and self.settings.llm_provider.lower() != "disabled")

    async def explain(self, system_prompt: str, user_prompt: str) -> str | None:
        if not self.enabled():
            return None
        # Bilerek doğrudan SDK bağımlılığı eklenmedi. Gerektiğinde resmi SDK ile implemente edilebilir.
        return None
