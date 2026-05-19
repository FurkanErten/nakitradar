from app.core.compat import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_LABELS_TR = {
    RiskLevel.LOW: "Düşük",
    RiskLevel.MEDIUM: "Orta",
    RiskLevel.HIGH: "Yüksek",
    RiskLevel.CRITICAL: "Kritik",
}

DEFAULT_TARGET_MARGIN = 0.18
FORECAST_DAYS = 30
