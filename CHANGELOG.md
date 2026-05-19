# Changelog

## 1.3.0 — Seçilebilir AI sağlayıcı final

- AI CFO sekmesine sağlayıcı seçimi eklendi: Otomatik, Ollama, Gemini, OpenAI, Yerel CFO.
- Üst menüye AI sağlayıcı seçimi eklendi.
- Backend `ChatRequest.llm_provider` ile her istek için sağlayıcı override destekliyor.
- Gemini API desteği eklendi (`google-genai`).
- Varsayılan otomatik sıra güncellendi: Ollama → Gemini → OpenAI → Yerel CFO fallback.
- `/api/ai/status` sağlayıcı seçeneklerini, Gemini/OpenAI yapılandırmasını ve Ollama erişimini döndürüyor.
- `.env.example`, README ve Windows kurulum dosyaları Gemini + seçilebilir AI yapısına göre güncellendi.

## 1.2.0 — Ollama local AI final

- AI Finans Sohbeti için Ollama local LLM desteği eklendi.
- Varsayılan LLM sırası `auto`: Ollama → OpenAI → yerel CFO fallback.
- OpenAI kota/billing olmadan ücretsiz demo yapılabilir hale getirildi.
- `naber`, `merhaba`, `selam` gibi küçük konuşmalar için finans analizi basmayan smalltalk filtresi eklendi.
- `/api/ai/status` artık Ollama erişilebilirliğini ve aktif provider sırasını gösteriyor.
- `OLLAMA_SETUP_WINDOWS.md` ve `setup_ollama_windows.ps1` eklendi.
- Frontend AI cevap etiketleri Ollama/OpenAI/fallback ayrımını gösterecek şekilde güncellendi.

## 1.1.0 — Windows/Python compatibility final

- Python 3.10 uyumluluğu eklendi.
- `enum.StrEnum` için `app.core.compat.StrEnum` fallback'i eklendi.
- PowerShell backend/frontend başlatma scriptleri eklendi.
- README Windows kurulum akışı Python 3.10 ve npm 10 için netleştirildi.
- Frontend `.npmrc` eklendi; install komutları audit/fund beklemeye takılmayacak şekilde düzenlendi.

## 1.0.0 — Pro MVP+

- Satış var, para yok analizi
- Kriz günü / nakit açığı simülatörü
- Ürün gerçek net kâr motoru
- What-if fiyat ve kriz senaryoları
- Tahsilat önceliklendirme
- CFO brifingi ve markdown raporu
