# NakitRadar AI — Ollama Local AI Kurulumu

Bu sürümde AI Finans Sohbeti varsayılan olarak şu sırayla çalışır:

```text
Ollama local AI → OpenAI API → Yerel CFO fallback
```

OpenAI API kotan yoksa sorun değil. Ollama bilgisayarında çalışır ve ücretsizdir.

---

## 1) Ollama kur

Sende `winget` görünmüyorsa normal; Windows'ta her sistemde yüklü olmayabiliyor.

En garanti yöntem:

```text
https://ollama.com/download/windows
```

Sayfadan Windows installer dosyasını indir, kur ve PowerShell'i kapatıp tekrar aç.

Kontrol:

```powershell
ollama --version
```

Eğer `ollama` hâlâ tanınmıyorsa:

```powershell
$env:Path += ";$env:LOCALAPPDATA\Programs\Ollama;C:\Program Files\Ollama"
ollama --version
```

---

## 2) Model indir

Hızlı ve hafif öneri:

```powershell
ollama pull qwen2.5:3b
```

Daha kaliteli ama daha ağır alternatif:

```powershell
ollama pull llama3.1:8b
```

Daha zayıf bilgisayar için:

```powershell
ollama pull qwen2.5:1.5b
```

---

## 3) Ollama çalışıyor mu test et

```powershell
ollama run qwen2.5:3b
```

Model cevap veriyorsa çalışıyor demektir. Çıkmak için `Ctrl + D` kullanabilirsin.

API servisi normalde otomatik olarak şu adreste çalışır:

```text
http://127.0.0.1:11434
```

---

## 4) Projede .env ayarı

Proje klasörü:

```powershell
$PROJECT_DIR="C:\Users\ferte\Desktop\nakitradar-ai-ollama-final"
```

Backend klasöründe `.env` dosyası oluştur:

```powershell
cd $PROJECT_DIR\backend
copy ..\.env.example .env
notepad .env
```

Ücretsiz local AI için en doğru ayar:

```env
LLM_PROVIDER=auto
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
OPENAI_API_KEY=
```

OpenAI API kotan varsa aynı dosyada `OPENAI_API_KEY` doldurabilirsin. Sistem önce Ollama'yı dener, Ollama çalışmazsa OpenAI'ye düşer.

---

## 5) Backend'i başlat

```powershell
cd $PROJECT_DIR\backend
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

AI durumunu kontrol et:

```text
http://127.0.0.1:8000/api/ai/status
```

Beklenen mantık:

```json
{
  "provider": "auto",
  "active_order": ["ollama"],
  "ollama_reachable": true
}
```

OpenAI key de varsa `active_order` şu olabilir:

```json
["ollama", "openai"]
```

---

## 6) Sık sorunlar

### `ollama_reachable: false`

Ollama servisi çalışmıyor olabilir. Şunu dene:

```powershell
ollama list
ollama run qwen2.5:3b
```

### Model bulunamadı hatası

`.env` içindeki model ile indirdiğin model aynı olmalı:

```powershell
ollama list
```

Örneğin listede `qwen2.5:3b` varsa `.env`:

```env
OLLAMA_MODEL=qwen2.5:3b
```

### Cevap çok yavaş

Daha küçük model kullan:

```powershell
ollama pull qwen2.5:1.5b
```

`.env`:

```env
OLLAMA_MODEL=qwen2.5:1.5b
```
