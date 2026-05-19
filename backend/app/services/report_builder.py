from __future__ import annotations

from app.domain.models import AnalysisResult, ScenarioCase
from app.services.advice_engine import money


def _scenario_line(case: ScenarioCase | None) -> str:
    if not case:
        return "| - | - | - | - | - |"
    return f"| {case.name} | {case.description} | {money(case.day_14_cash)} | {money(case.cash_gap)} | {case.interpretation} |"


class ReportBuilder:
    def markdown(self, result: AnalysisResult) -> str:
        lines: list[str] = []
        lines.append("# NakitRadar AI CFO Raporu")
        lines.append("")
        lines.append(f"**İşletme:** {result.profile.business_name}")
        lines.append(f"**Analiz tarihi:** {result.analysis_date.isoformat()}")
        lines.append(f"**Risk skoru:** {result.risk.total_score:.0f}/100")
        lines.append("")
        lines.append("## Yönetici Özeti")
        lines.append(result.summary.headline)
        lines.append("")
        lines.append(result.summary.narrative)
        lines.append("")
        lines.append("## Satış Var, Para Yok Analizi")
        fs = result.financial_snapshot
        lines.append(f"- Brüt satış: **{money(fs.gross_sales)}**")
        lines.append(f"- Kağıt üstü kâr: **{money(fs.paper_profit)}**")
        lines.append(f"- Gerçek net kâr: **{money(fs.real_net_profit)}**")
        lines.append(f"- Pazaryeri + ödeme kesintileri: **{money(fs.marketplace_costs)}**")
        lines.append(f"- Kargo + paketleme: **{money(fs.shipping_and_packaging_costs)}**")
        lines.append(f"- Geciken alacak: **{money(fs.overdue_receivables)}**")
        lines.append(f"- Stokta kilitlenen nakit: **{money(fs.locked_inventory_cash)}**")
        lines.append("")
        lines.append("## Kriz Uyarısı")
        lines.append(f"**{result.crisis_alert.title}**")
        lines.append(result.crisis_alert.description)
        if result.crisis_alert.critical_day:
            lines.append(f"**Kritik gün:** {result.crisis_alert.critical_day.isoformat()}")
            lines.append(f"**Beklenen nakit açığı:** {money(result.crisis_alert.cash_gap)}")
        lines.append("")
        lines.append("### Kök sebepler")
        for r in result.crisis_alert.root_causes:
            lines.append(f"- {r}")
        lines.append("")
        lines.append("## Bugünkü aksiyonlar")
        for i, action in enumerate(result.actions, start=1):
            lines.append(f"{i}. **{action.title}** — {action.detail} _Etki:_ {action.impact}")
        lines.append("")
        lines.append("## Senaryo Simülasyonu")
        lines.append("| Senaryo | Açıklama | 14. gün kasası | Açık | Yorum |")
        lines.append("|---|---|---:|---:|---|")
        suite = result.scenario_suite
        lines.append(_scenario_line(suite.base_case))
        lines.append(_scenario_line(suite.top_receivable_collected))
        lines.append(_scenario_line(suite.stock_purchase_frozen))
        lines.append(_scenario_line(suite.price_fix_applied))
        lines.append(_scenario_line(suite.combined_rescue))
        lines.append("")
        lines.append("## Ürün kârlılığı")
        lines.append("| Ürün | Durum | Net kâr | Marj | Güvenli indirim | Önerilen fiyat |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for p in result.product_profitability:
            lines.append(f"| {p.name} | {p.status} | {money(p.net_profit)} | %{p.margin*100:.1f} | %{p.safe_campaign_discount_percent:.1f} | {money(p.recommended_price)} |")
        lines.append("")
        lines.append("## Tahsilat öncelikleri")
        if not result.receivable_priorities:
            lines.append("Geciken veya açık alacak bulunmuyor.")
        else:
            for r in result.receivable_priorities[:5]:
                lines.append(f"- **{r.customer_name}**: {money(r.amount)}, gecikme {r.delay_days} gün, öncelik {r.priority_score:.0f}/100")
        lines.append("")
        lines.append("## Veri Kalitesi")
        if not result.data_quality_issues:
            lines.append("Kritik veri kalitesi problemi görünmüyor.")
        else:
            for issue in result.data_quality_issues:
                lines.append(f"- **{issue.severity} / {issue.entity}:** {issue.message} Öneri: {issue.recommendation}")
        lines.append("")
        lines.append("## Nakit akışı ilk 14 gün")
        lines.append("| Tarih | Giriş | Çıkış | Kapanış |")
        lines.append("|---|---:|---:|---:|")
        for p in result.cashflow[:14]:
            lines.append(f"| {p.date.isoformat()} | {money(p.expected_inflow)} | {money(p.expected_outflow)} | {money(p.closing_cash)} |")
        return "\n".join(lines)
