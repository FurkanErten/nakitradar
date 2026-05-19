from __future__ import annotations

import shutil
import tempfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.domain.models import (
    AnalysisResult,
    BusinessInput,
    ChatRequest,
    ChatResponse,
    CollectionMessageRequest,
    CollectionMessageResponse,
    CrisisScenarioRequest,
    PriceScenarioRequest,
    PriceScenarioResult,
    ScenarioSuite,
)
from app.services.advice_engine import AdviceEngine
from app.services.csv_loader import (
    DataLoadError,
    load_business_from_folder,
    load_orders,
    load_payables,
    load_products,
    load_receivables,
    load_transactions,
)
from app.services.finance_engine import FinanceEngine
from app.services.report_builder import ReportBuilder
from app.services.ai_cfo_service import AICFOService

router = APIRouter(prefix="/api", tags=["analysis"])

_SAMPLE_CANDIDATES = [
    Path(__file__).resolve().parents[3] / "samples",
    Path(__file__).resolve().parents[2] / "samples",
    Path.cwd() / "samples",
]
SAMPLES_DIR = next((p for p in _SAMPLE_CANDIDATES if p.exists()), _SAMPLE_CANDIDATES[0])
DATASETS_DIR = SAMPLES_DIR / "datasets"


def _dataset_folder(dataset_key: str | None = None) -> Path:
    if not dataset_key or dataset_key == "default":
        return SAMPLES_DIR
    key = dataset_key.strip().lower()
    candidate = DATASETS_DIR / key
    if not candidate.exists() or not candidate.is_dir():
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_key}")
    return candidate


def get_demo_business(dataset_key: str | None = None) -> BusinessInput:
    defaults = {
        "default": (64000, date(2026, 5, 16)),
        "crisis_ecommerce": (52000, date(2026, 5, 16)),
        "healthy_growth": (145000, date(2026, 5, 16)),
        "restaurant_cashflow": (38000, date(2026, 5, 16)),
        "instagram_boutique": (28000, date(2026, 5, 16)),
    }
    key = dataset_key or "default"
    cash, d = defaults.get(key, defaults["default"])
    return load_business_from_folder(_dataset_folder(dataset_key), cash_balance=cash, analysis_date=d)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "NakitRadar AI"}


@router.get("/datasets")
def list_datasets() -> dict[str, list[dict[str, str]]]:
    items = [
        {"key": "default", "name": "Varsayılan demo", "description": "Karma e-ticaret: nakit riski ve zarar eden ürünler"}
    ]
    if DATASETS_DIR.exists():
        names = {
            "crisis_ecommerce": ("Krizde e-ticaret satıcısı", "Yüksek komisyon, geciken alacak, yaklaşan ödeme baskısı"),
            "healthy_growth": ("Sağlıklı büyüyen mağaza", "Kârlı ürünler, düşük iade, kontrollü stok"),
            "restaurant_cashflow": ("Restoran / kafe nakit akışı", "Günlük gelir, kira/maaş, tedarikçi ödemeleri"),
            "instagram_boutique": ("Instagram butik", "Düşük nakit, iade/kargo baskısı, stokta kilitli para"),
        }
        for folder in sorted(DATASETS_DIR.iterdir()):
            if folder.is_dir():
                name, desc = names.get(folder.name, (folder.name.replace("_", " ").title(), "Test veri seti"))
                items.append({"key": folder.name, "name": name, "description": desc})
    return {"datasets": items}


@router.get("/demo", response_model=AnalysisResult)
def demo_analysis() -> AnalysisResult:
    return FinanceEngine().analyze(get_demo_business())


@router.get("/demo/{dataset_key}", response_model=AnalysisResult)
def demo_dataset_analysis(dataset_key: str) -> AnalysisResult:
    return FinanceEngine().analyze(get_demo_business(dataset_key))


@router.post("/analyze", response_model=AnalysisResult)
def analyze(payload: BusinessInput) -> AnalysisResult:
    return FinanceEngine().analyze(payload)


def _save_upload(file: UploadFile | None, folder: Path, target_name: str) -> Path | None:
    if file is None:
        return None
    suffix = Path(file.filename or target_name).suffix or ".csv"
    target = folder / f"{target_name}{suffix}"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return target


@router.post("/upload", response_model=AnalysisResult)
async def upload_analysis(
    cash_balance: float = Form(...),
    analysis_date: date | None = Form(None),
    business_name: str = Form("Yüklenen İşletme"),
    products_file: UploadFile | None = File(None),
    orders_file: UploadFile | None = File(None),
    transactions_file: UploadFile | None = File(None),
    receivables_file: UploadFile | None = File(None),
    payables_file: UploadFile | None = File(None),
) -> AnalysisResult:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            paths = {
                "products": _save_upload(products_file, folder, "products"),
                "orders": _save_upload(orders_file, folder, "orders"),
                "transactions": _save_upload(transactions_file, folder, "transactions"),
                "receivables": _save_upload(receivables_file, folder, "receivables"),
                "payables": _save_upload(payables_file, folder, "payables"),
            }
            business = BusinessInput(
                cash_balance=cash_balance,
                analysis_date=analysis_date or date.today(),
                profile={"business_name": business_name, "sector": "Yüklenen veri"},
                products=load_products(paths["products"]) if paths["products"] else [],
                orders=load_orders(paths["orders"]) if paths["orders"] else [],
                transactions=load_transactions(paths["transactions"]) if paths["transactions"] else [],
                receivables=load_receivables(paths["receivables"]) if paths["receivables"] else [],
                payables=load_payables(paths["payables"]) if paths["payables"] else [],
            )
            return FinanceEngine().analyze(business)
    except DataLoadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/what-if/price", response_model=PriceScenarioResult)
def price_scenario(req: PriceScenarioRequest) -> PriceScenarioResult:
    business = get_demo_business(req.dataset_key) if req.use_demo else req.business_input
    if business is None:
        raise HTTPException(status_code=400, detail="business_input is required when use_demo=false")
    try:
        return FinanceEngine().price_scenario(business, req.sku, req.new_price)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/what-if/crisis", response_model=ScenarioSuite)
def crisis_scenario(req: CrisisScenarioRequest) -> ScenarioSuite:
    business = get_demo_business(req.dataset_key) if req.use_demo else req.business_input
    if business is None:
        raise HTTPException(status_code=400, detail="business_input is required when use_demo=false")
    return FinanceEngine().analyze(business).scenario_suite


@router.post("/collection-message", response_model=CollectionMessageResponse)
def collection_message(req: CollectionMessageRequest) -> CollectionMessageResponse:
    return CollectionMessageResponse(message=AdviceEngine().collection_message(req))


@router.get("/ai/status")
def ai_status() -> dict:
    return AICFOService().status()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    business = get_demo_business(req.dataset_key) if req.use_demo else req.business_input
    if business is None:
        raise HTTPException(status_code=400, detail="business_input is required when use_demo=false")
    result = FinanceEngine().analyze(business)
    return AICFOService().answer(req, business, result)


@router.get("/report/demo.md", response_class=PlainTextResponse)
def demo_report() -> str:
    result = FinanceEngine().analyze(get_demo_business())
    return ReportBuilder().markdown(result)


@router.get("/templates/readme", response_class=PlainTextResponse)
def templates_readme() -> str:
    return """NakitRadar CSV şablonları

Zorunlu dosyalar:
- products.csv: sku,name,category,unit_cost,sale_price,stock_count,monthly_sales_velocity
- orders.csv: order_id,sku,order_date,sale_price,quantity,commission,shipping_cost,packaging_cost,ad_cost,payment_fee,is_returned,return_cost
- receivables.csv: id,customer_name,amount,due_date,probability,status
- payables.csv: id,vendor_name,amount,due_date,category,is_fixed
- transactions.csv: id,date,description,amount,type,category

Tüm tarihler YYYY-MM-DD formatında olmalıdır.
"""
