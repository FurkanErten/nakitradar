from datetime import date
from pathlib import Path

from app.services.csv_loader import load_business_from_folder
from app.services.finance_engine import FinanceEngine

ROOT = Path(__file__).resolve().parents[2]


def test_demo_has_cash_gap_and_actions():
    business = load_business_from_folder(ROOT / "samples", cash_balance=64000, analysis_date=date(2026, 5, 16))
    result = FinanceEngine().analyze(business)
    assert result.risk.total_score > 0
    assert len(result.actions) >= 3
    assert result.summary.cash_gap >= 0


def test_price_scenario_returns_interpretation():
    business = load_business_from_folder(ROOT / "samples", cash_balance=64000, analysis_date=date(2026, 5, 16))
    scenario = FinanceEngine().price_scenario(business, "SP-003", 469)
    assert scenario.sku == "SP-003"
    assert scenario.new_price == 469
    assert scenario.interpretation
