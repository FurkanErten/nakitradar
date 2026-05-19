# NakitRadar AI — Windows hızlı başlatma

> Klasörü farklı adla çıkardıysan sadece `PROJECT_DIR` satırını değiştir.

## 0) Proje klasörü

```powershell
$PROJECT_DIR="C:\Users\<KULLANICI_ADI>\Desktop\nakitradar-ai-ai-selector-final"
cd $PROJECT_DIR
```

Eğer klasör adın farklıysa örnek:

```powershell
$PROJECT_DIR="C:\Users\ferte\Desktop\nakitradar-ai-ollama-final"
```

## 1) Backend

```powershell
cd $PROJECT_DIRackend
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
copy ..\.env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

Kontrol:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/ai/status
```

## 2) AI sağlayıcı ayarı

`.env` dosyasını aç:

```powershell
notepad $PROJECT_DIRackend\.env
```

Varsayılan önerilen ayar:

```env
LLM_PROVIDER=auto
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
```

Arayüzden seçilebilen seçenekler:

```text
Otomatik → Ollama → Gemini → OpenAI → Yerel CFO
Ollama Local
Gemini API
OpenAI GPT
Yerel CFO
```

## 3) Ollama kurulumu

Ollama yüklü değilse manuel kur:

```text
https://ollama.com/download/windows
```

Kurulumdan sonra PowerShell’i kapat-aç:

```powershell
ollama --version
ollama pull qwen2.5:3b
ollama run qwen2.5:3b
```

Çıkmak için:

```text
/bye
```

## 4) Gemini API kullanmak için

Google AI Studio’dan key al:

```text
https://aistudio.google.com/app/apikey
```

`.env` içine:

```env
GEMINI_API_KEY=BURAYA_GERCEK_KEY
GEMINI_MODEL=gemini-2.5-flash
```

Backend’i yeniden başlat.

## 5) OpenAI API kullanmak için

`.env` içine:

```env
OPENAI_API_KEY=BURAYA_GERCEK_KEY
OPENAI_MODEL=gpt-5-mini
```

Backend’i yeniden başlat.

## 6) Frontend

Yeni PowerShell aç:

```powershell
cd $PROJECT_DIRrontend
npm install --no-audit --no-fund
npm run dev
```

Kontrol:

```text
http://127.0.0.1:5173
```

## 7) Sık hatalar

### Python 3.14 / pydantic-core / Rust hatası

Yanlış Python ile venv kurmuşsun. Şunu kullan:

```powershell
py -3.10 -m venv .venv
```

### vite is not recognized

```powershell
cd $PROJECT_DIRrontend
npm install --no-audit --no-fund
npm run dev
```

### Gemini seçtim ama yerel fallback oldu

- `GEMINI_API_KEY` boş olabilir.
- Backend yeniden başlatılmamış olabilir.
- `pip install -r requirements.txt` tekrar çalıştırılmalı; `google-genai` kurulmalı.

### OpenAI insufficient_quota

OpenAI API hesabında kota/billing yok. Ollama veya Gemini seç.
