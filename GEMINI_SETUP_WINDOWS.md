# Gemini API Kurulumu — NakitRadar AI

Bu proje Gemini API'yi opsiyonel AI sağlayıcı olarak destekler.

## 1) API key alma

Google AI Studio'ya gir:

```text
https://aistudio.google.com/app/apikey
```

Yeni API key oluştur. Anahtarı kimseyle paylaşma.

## 2) Backend .env ayarı

```powershell
cd backend
notepad .env
```

Şunları doldur:

```env
LLM_PROVIDER=auto
GEMINI_API_KEY=BURAYA_GERCEK_KEY
GEMINI_MODEL=gemini-2.5-flash
```

Sadece Gemini kullanmak istersen:

```env
LLM_PROVIDER=gemini
```

## 3) Paket kurulumu

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Bu komut `google-genai` paketini kurar.

## 4) Backend yeniden başlat

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

## 5) Arayüzden seç

Frontend’de üst menüden veya AI CFO sekmesinden:

```text
AI: Gemini
```

seç.

## 6) Çalışma sırası

`LLM_PROVIDER=auto` ise sıra:

```text
Ollama Local → Gemini API → OpenAI GPT → Yerel CFO fallback
```

Gemini key yoksa otomatik olarak diğer sağlayıcıya veya fallback moduna geçer.
