# NakitRadar AI — Seçilebilir AI Final

KOBİ ve e-ticaret satıcıları için yapay zekâ destekli **Mini CFO** uygulaması.

Bu final sürümde AI Finans Sohbeti tarafına siteden seçilebilir sağlayıcı eklendi:

```txt
Otomatik: Ollama Local → Gemini API → OpenAI GPT → Yerel CFO fallback
```

Kullanıcı arayüzden şu seçeneklerden birini seçebilir:

- **Otomatik**: önce Ollama, sonra Gemini, sonra OpenAI, en son yerel CFO
- **Ollama Local**: ücretsiz yerel model
- **Gemini API**: Google Gemini API
- **OpenAI GPT**: OpenAI API
- **Yerel CFO**: API kullanmayan kural tabanlı mod

Finansal hesapları LLM yapmaz. Net kâr, nakit akışı, ürün fiyat simülasyonu, tahsilat önceliği ve risk skorları Python finans motorunda hesaplanır. AI sadece bu sonuçları anlaşılır CFO cevabına çevirir.

## Özellikler

- 30 günlük nakit akışı tahmini
- “Satış var, para yok” analizi
- Kağıt üstü kâr vs gerçek net kâr ayrımı
- Ürün bazlı net kâr hesabı
- Komisyon, ödeme kesintisi, kargo, paketleme, reklam, iade ve stok maliyeti dahil kârlılık
- Zarar ettiren ürün dedektörü
- Akıllı fiyat önerisi ve güvenli indirim hesabı
- What-if fiyat simülasyonu
- Tahsilat önceliklendirme
- Otomatik tahsilat mesajı
- Stokta kilitlenen para analizi
- Günlük CFO aksiyon listesi
- Seçilebilir AI sağlayıcı: Ollama / Gemini / OpenAI / Yerel CFO
- CSV/Excel yükleme
- Çoklu demo veri seti

## Kurulum — Windows

### Backend

```powershell
cd backend
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
copy ..\.env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

API dokümantasyonu:

```text
http://127.0.0.1:8000/docs
```

AI durum kontrolü:

```text
http://127.0.0.1:8000/api/ai/status
```

### Frontend

Yeni PowerShell aç:

```powershell
cd frontend
npm install --no-audit --no-fund
npm run dev
```

Uygulama:

```text
http://127.0.0.1:5173
```

## .env ayarı

Backend klasöründe `.env` dosyası olmalı:

```powershell
cd backend
copy ..\.env.example .env
notepad .env
```

Örnek:

```env
APP_ENV=development
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

LLM_PROVIDER=auto

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT_SECONDS=60

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT_SECONDS=25

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
OPENAI_TIMEOUT_SECONDS=25
```

## Ollama local AI

Ücretsiz local kullanım için:

```powershell
ollama pull qwen2.5:3b
ollama run qwen2.5:3b
```

Çıkış:

```text
/bye
```

## Gemini API

Google AI Studio’dan Gemini API key oluştur:

```text
https://aistudio.google.com/app/apikey
```

Sonra `.env` içine koy:

```env
GEMINI_API_KEY=buraya_anahtarin
GEMINI_MODEL=gemini-2.5-flash
```

Backend’i yeniden başlat:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Arayüzde AI sağlayıcı seçeneğinden **Gemini API** seç.

## OpenAI API

OpenAI API kotan varsa:

```env
OPENAI_API_KEY=buraya_anahtarin
OPENAI_MODEL=gpt-5-mini
```

Arayüzden **OpenAI GPT** seç.

## Test veri setleri

`/samples/datasets` altında senaryolar var:

- `crisis_ecommerce`
- `healthy_growth`
- `restaurant_cashflow`
- `instagram_boutique`

Frontend üst menüden veri seti seçilebilir.

## CSV dosya formatları

- `products.csv`: `sku,name,category,unit_cost,sale_price,stock_count,monthly_sales_velocity`
- `orders.csv`: `order_id,sku,order_date,sale_price,quantity,commission,shipping_cost,packaging_cost,ad_cost,payment_fee,is_returned,return_cost`
- `transactions.csv`: `id,date,description,amount,type,category`
- `receivables.csv`: `id,customer_name,amount,due_date,probability,status`
- `payables.csv`: `id,vendor_name,amount,due_date,category,is_fixed`

Tarihler `YYYY-MM-DD` formatında olmalı.

## GitHub için kritik not

`.env` dosyasını GitHub’a yükleme. API key sadece local bilgisayarda kalmalı.
