from __future__ import annotations

from datetime import date, datetime
from app.core.compat import StrEnum
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.core.constants import RiskLevel


class TxType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class ReceivableStatus(StrEnum):
    UNPAID = "unpaid"
    PAID = "paid"
    CANCELLED = "cancelled"


class DataSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class BusinessProfile(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    business_name: str = "Demo İşletme"
    sector: str = "E-ticaret"
    monthly_revenue_target: float = Field(0, ge=0)
    owner_email: str | None = None


class Product(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    category: str = "Genel"
    unit_cost: float = Field(..., ge=0)
    sale_price: float = Field(..., ge=0)
    stock_count: int = Field(0, ge=0)
    monthly_sales_velocity: float = Field(0, ge=0, description="Son dönem aylık ortalama satış adedi")
    min_stock_count: int = Field(0, ge=0)
    vat_rate: float = Field(0.10, ge=0, le=1)
    storage_cost_per_unit_day: float = Field(0, ge=0)


class Order(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    order_id: str
    sku: str
    order_date: date
    sale_price: float = Field(..., ge=0)
    quantity: int = Field(1, ge=1)
    commission: float = Field(0, ge=0)
    shipping_cost: float = Field(0, ge=0)
    packaging_cost: float = Field(0, ge=0)
    ad_cost: float = Field(0, ge=0)
    payment_fee: float = Field(0, ge=0)
    is_returned: bool = False
    return_cost: float = Field(0, ge=0)


class Transaction(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    date: date
    description: str
    amount: float = Field(..., ge=0)
    type: TxType
    category: str = "Genel"


class Receivable(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    customer_name: str
    amount: float = Field(..., ge=0)
    due_date: date
    probability: float = Field(0.85, ge=0, le=1)
    status: ReceivableStatus = ReceivableStatus.UNPAID


class Payable(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    vendor_name: str
    amount: float = Field(..., ge=0)
    due_date: date
    category: str = "Genel"
    is_fixed: bool = False


class BusinessInput(BaseModel):
    analysis_date: date = Field(default_factory=date.today)
    cash_balance: float = Field(..., ge=0)
    profile: BusinessProfile = Field(default_factory=BusinessProfile)
    products: list[Product] = Field(default_factory=list)
    orders: list[Order] = Field(default_factory=list)
    transactions: list[Transaction] = Field(default_factory=list)
    receivables: list[Receivable] = Field(default_factory=list)
    payables: list[Payable] = Field(default_factory=list)
    target_margin: float = Field(0.18, ge=0.01, le=0.80)
    tax_rate: float = Field(0.20, ge=0, le=1)
    marketplace_payout_delay_days: int = Field(12, ge=0, le=60)


class CashFlowPoint(BaseModel):
    date: date
    opening_cash: float
    expected_inflow: float
    expected_outflow: float
    closing_cash: float
    notes: list[str] = Field(default_factory=list)


class ProductProfitability(BaseModel):
    sku: str
    name: str
    category: str
    units_sold: int
    revenue: float
    total_cost: float
    net_profit: float
    margin: float
    return_rate: float
    avg_profit_per_unit: float
    current_price: float
    break_even_price: float
    recommended_price: float
    max_safe_discount_percent: float
    stock_value: float
    days_of_inventory: float | None
    health_score: float
    status: Literal["grow", "watch", "liquidate", "stop"]
    reasons: list[str]
    commission_rate: float = 0
    ad_rate: float = 0
    payment_fee_rate: float = 0
    average_shipping_cost: float = 0
    average_return_cost: float = 0
    safe_campaign_discount_percent: float = 0
    next_step: str = "İzle"


class ReceivablePriority(BaseModel):
    id: str
    customer_name: str
    amount: float
    due_date: date
    delay_days: int
    probability: float
    priority_score: float
    level: RiskLevel
    impact: str
    suggested_message: str
    collection_strategy: Literal["soft", "balanced", "firm", "legal_warning"] = "balanced"


class InventoryRisk(BaseModel):
    sku: str
    name: str
    stock_count: int
    stock_value: float
    days_of_inventory: float | None
    risk_level: RiskLevel
    action: str
    locked_cash_ratio: float = 0


class RiskBreakdown(BaseModel):
    payment_pressure: float
    receivable_risk: float
    low_profit_product_risk: float
    stock_locked_risk: float
    revenue_uncertainty: float
    total_score: float
    level: RiskLevel


class FinancialSnapshot(BaseModel):
    gross_sales: float
    paper_profit: float
    real_net_profit: float
    marketplace_costs: float
    shipping_and_packaging_costs: float
    return_costs: float
    ad_spend: float
    overdue_receivables: float
    locked_inventory_cash: float
    cash_conversion_gap: float
    loss_making_products_count: int
    dangerous_campaign_products_count: int


class CrisisAlert(BaseModel):
    title: str
    description: str
    critical_day: date | None
    minimum_cash: float
    cash_gap: float
    root_causes: list[str]
    survival_plan: list[str]


class ScenarioCase(BaseModel):
    name: str
    description: str
    day_14_cash: float
    minimum_cash: float
    cash_gap: float
    risk_score: float
    interpretation: str


class ScenarioSuite(BaseModel):
    base_case: ScenarioCase
    top_receivable_collected: ScenarioCase | None = None
    stock_purchase_frozen: ScenarioCase | None = None
    price_fix_applied: ScenarioCase | None = None
    combined_rescue: ScenarioCase | None = None


class DataQualityIssue(BaseModel):
    severity: DataSeverity
    entity: str
    message: str
    recommendation: str


class DailyCFOBrief(BaseModel):
    morning_summary: str
    top_priorities: list[str]
    forbidden_actions: list[str]
    safe_actions: list[str]


class IntegrationConnector(BaseModel):
    name: str
    category: Literal["marketplace", "banking", "accounting", "shipping", "ads", "communication"]
    status: Literal["ready_for_csv", "api_planned", "manual"]
    data_needed: list[str]
    value: str


class ActionItem(BaseModel):
    title: str
    detail: str
    impact: str
    priority: Literal["critical", "high", "medium", "low"]
    category: Literal["cashflow", "receivable", "pricing", "inventory", "marketplace", "general", "data", "security"]


class ExecutiveSummary(BaseModel):
    headline: str
    narrative: str
    critical_day: date | None
    minimum_cash: float
    cash_gap: float
    top_risks: list[str]
    today_actions: list[str]


class AnalysisResult(BaseModel):
    generated_at: datetime
    analysis_date: date
    profile: BusinessProfile
    summary: ExecutiveSummary
    financial_snapshot: FinancialSnapshot
    crisis_alert: CrisisAlert
    risk: RiskBreakdown
    cashflow: list[CashFlowPoint]
    product_profitability: list[ProductProfitability]
    receivable_priorities: list[ReceivablePriority]
    inventory_risks: list[InventoryRisk]
    scenario_suite: ScenarioSuite
    daily_brief: DailyCFOBrief
    data_quality_issues: list[DataQualityIssue]
    integration_roadmap: list[IntegrationConnector]
    actions: list[ActionItem]


class PriceScenarioRequest(BaseModel):
    sku: str
    new_price: float = Field(..., gt=0)
    use_demo: bool = True
    dataset_key: str | None = None
    business_input: BusinessInput | None = None


class PriceScenarioResult(BaseModel):
    sku: str
    old_price: float
    new_price: float
    old_profit_per_unit: float
    new_profit_per_unit: float
    old_margin: float
    new_margin: float
    estimated_sales_change_percent: float
    projected_monthly_profit_delta: float
    break_even_price: float
    recommended_price: float
    old_safe_discount_percent: float
    new_safe_discount_percent: float
    interpretation: str


class CrisisScenarioRequest(BaseModel):
    use_demo: bool = True
    dataset_key: str | None = None
    business_input: BusinessInput | None = None


class CollectionMessageRequest(BaseModel):
    customer_name: str
    amount: float = Field(..., gt=0)
    delay_days: int = Field(0, ge=0)
    tone: Literal["soft", "balanced", "firm", "legal_warning"] = "balanced"


class CollectionMessageResponse(BaseModel):
    message: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2)
    use_demo: bool = True
    dataset_key: str | None = None
    business_input: BusinessInput | None = None
    llm_provider: Literal["auto", "ollama", "gemini", "openai", "disabled", "local"] = "auto"


class ChatResponse(BaseModel):
    answer: str
    provider: Literal["local", "openai", "ollama", "gemini", "error_fallback"] = "local"
    model: str | None = None
    used_tools: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
