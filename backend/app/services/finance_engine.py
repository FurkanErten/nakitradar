from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from math import isfinite
from copy import deepcopy

from app.core.constants import FORECAST_DAYS, RiskLevel
from app.domain.models import (
    ActionItem,
    AnalysisResult,
    BusinessInput,
    CashFlowPoint,
    CrisisAlert,
    DailyCFOBrief,
    DataQualityIssue,
    DataSeverity,
    ExecutiveSummary,
    FinancialSnapshot,
    IntegrationConnector,
    InventoryRisk,
    Order,
    PriceScenarioResult,
    Product,
    ProductProfitability,
    Receivable,
    ReceivablePriority,
    ReceivableStatus,
    CollectionMessageRequest,
    RiskBreakdown,
    ScenarioCase,
    ScenarioSuite,
    Transaction,
    TxType,
)
from app.services.advice_engine import AdviceEngine, money


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    if not isfinite(value):
        return low
    return max(low, min(high, value))


def risk_level(score: float) -> RiskLevel:
    if score >= 80:
        return RiskLevel.CRITICAL
    if score >= 60:
        return RiskLevel.HIGH
    if score >= 35:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


@dataclass(frozen=True)
class ProductCostProfile:
    commission_rate: float = 0
    payment_rate: float = 0
    ad_rate: float = 0
    average_shipping: float = 0
    average_packaging: float = 0
    average_return_cost: float = 0
    return_rate: float = 0
    average_storage_cost: float = 0


class FinanceEngine:
    """Deterministic finance engine.

    Kritik prensip: finansal hesaplar LLM'e bırakılmaz. Bu sınıf kesin, izlenebilir
    formüllerle kâr, nakit, risk ve senaryo analizi üretir; AdviceEngine yalnızca
    bu sayıları kullanıcı diline çevirir.
    """

    def __init__(self, advice: AdviceEngine | None = None):
        self.advice = advice or AdviceEngine()

    def analyze(self, business: BusinessInput) -> AnalysisResult:
        products = {p.sku: p for p in business.products}
        cashflow = self._build_cashflow(business)
        product_profitability = self._product_profitability(business, products)
        receivable_priorities = self._receivable_priorities(business, cashflow)
        inventory_risks = self._inventory_risks(business, product_profitability)
        snapshot = self._financial_snapshot(business, product_profitability, receivable_priorities, inventory_risks)
        risk = self._risk_breakdown(business, cashflow, product_profitability, receivable_priorities, inventory_risks)
        actions = self._actions(business, cashflow, product_profitability, receivable_priorities, inventory_risks, risk)
        summary = self._summary(cashflow, risk, actions, product_profitability, receivable_priorities)
        crisis = self._crisis_alert(cashflow, snapshot, product_profitability, receivable_priorities, inventory_risks, actions)
        scenario_suite = self._scenario_suite(business, product_profitability)
        data_quality = self._data_quality_issues(business, product_profitability)
        daily_brief = self._daily_brief(summary, crisis, actions, scenario_suite)
        roadmap = self._integration_roadmap()

        return AnalysisResult(
            generated_at=datetime.now(timezone.utc),
            analysis_date=business.analysis_date,
            profile=business.profile,
            summary=summary,
            financial_snapshot=snapshot,
            crisis_alert=crisis,
            risk=risk,
            cashflow=cashflow,
            product_profitability=product_profitability,
            receivable_priorities=receivable_priorities,
            inventory_risks=inventory_risks,
            scenario_suite=scenario_suite,
            daily_brief=daily_brief,
            data_quality_issues=data_quality,
            integration_roadmap=roadmap,
            actions=actions,
        )

    def _build_cashflow(self, business: BusinessInput, days: int = FORECAST_DAYS) -> list[CashFlowPoint]:
        start = business.analysis_date
        daily_in: dict[date, list[tuple[float, str]]] = defaultdict(list)
        daily_out: dict[date, list[tuple[float, str]]] = defaultdict(list)

        for tx in business.transactions:
            if tx.date < start:
                continue
            target = tx.date
            if tx.type == TxType.INCOME:
                daily_in[target].append((tx.amount, tx.description))
            else:
                daily_out[target].append((tx.amount, tx.description))

        for rec in business.receivables:
            if rec.status != ReceivableStatus.UNPAID:
                continue
            target = max(rec.due_date, start)
            daily_in[target].append((rec.amount * rec.probability, f"Beklenen tahsilat: {rec.customer_name}"))

        for pay in business.payables:
            target = max(pay.due_date, start)
            daily_out[target].append((pay.amount, f"Ödeme: {pay.vendor_name}"))

        points: list[CashFlowPoint] = []
        cash = business.cash_balance
        for i in range(days):
            day = start + timedelta(days=i)
            opening = cash
            inflow_items = daily_in.get(day, [])
            outflow_items = daily_out.get(day, [])
            inflow = sum(v for v, _ in inflow_items)
            outflow = sum(v for v, _ in outflow_items)
            cash = opening + inflow - outflow
            notes = [name for _, name in inflow_items[:3]] + [name for _, name in outflow_items[:3]]
            points.append(
                CashFlowPoint(
                    date=day,
                    opening_cash=round(opening, 2),
                    expected_inflow=round(inflow, 2),
                    expected_outflow=round(outflow, 2),
                    closing_cash=round(cash, 2),
                    notes=notes,
                )
            )
        return points

    def _order_profit(self, order: Order, product: Product | None) -> tuple[float, float, float]:
        unit_cost = product.unit_cost if product else 0
        revenue = 0 if order.is_returned else order.sale_price * order.quantity
        product_cost = unit_cost * order.quantity
        total_cost = (
            product_cost
            + order.commission
            + order.shipping_cost
            + order.packaging_cost
            + order.ad_cost
            + order.payment_fee
            + (order.return_cost if order.is_returned else 0)
        )
        return revenue, total_cost, revenue - total_cost

    def _cost_profile(self, orders: list[Order], product: Product) -> ProductCostProfile:
        total_order_units = sum(o.quantity for o in orders) or 1
        gross_order_value = sum(o.sale_price * o.quantity for o in orders) or max(product.sale_price, 1)
        commission = sum(o.commission for o in orders)
        payment = sum(o.payment_fee for o in orders)
        ad = sum(o.ad_cost for o in orders)
        shipping = sum(o.shipping_cost for o in orders)
        packaging = sum(o.packaging_cost for o in orders)
        return_cost = sum(o.return_cost for o in orders if o.is_returned)
        returned_count = sum(o.quantity for o in orders if o.is_returned)
        return ProductCostProfile(
            commission_rate=commission / gross_order_value,
            payment_rate=payment / gross_order_value,
            ad_rate=ad / gross_order_value,
            average_shipping=shipping / total_order_units,
            average_packaging=packaging / total_order_units,
            average_return_cost=return_cost / total_order_units,
            return_rate=returned_count / total_order_units,
            average_storage_cost=product.storage_cost_per_unit_day * 30,
        )

    def _unit_profit_at_price(self, price: float, product: Product, profile: ProductCostProfile) -> tuple[float, float, float]:
        variable_rates = profile.commission_rate + profile.payment_rate + profile.ad_rate
        variable_cost = price * variable_rates
        fixed_unit_cost = (
            product.unit_cost
            + profile.average_shipping
            + profile.average_packaging
            + profile.average_return_cost
            + profile.average_storage_cost
        )
        unit_profit = price - fixed_unit_cost - variable_cost
        margin = unit_profit / price if price else 0
        break_even = fixed_unit_cost / max(0.05, 1 - variable_rates)
        return unit_profit, margin, break_even

    def _product_profitability(self, business: BusinessInput, products: dict[str, Product]) -> list[ProductProfitability]:
        orders_by_sku: dict[str, list[Order]] = defaultdict(list)
        for order in business.orders:
            orders_by_sku[order.sku].append(order)

        results: list[ProductProfitability] = []
        for sku, product in products.items():
            orders = orders_by_sku.get(sku, [])
            revenue = total_cost = net_profit = 0.0
            units_sold = 0
            returned_count = 0

            for order in orders:
                r, c, p = self._order_profit(order, product)
                revenue += r
                total_cost += c
                net_profit += p
                if not order.is_returned:
                    units_sold += order.quantity
                else:
                    returned_count += order.quantity

            profile = self._cost_profile(orders, product)
            variable_rates = profile.commission_rate + profile.payment_rate + profile.ad_rate
            fixed_unit_cost = (
                product.unit_cost
                + profile.average_shipping
                + profile.average_packaging
                + profile.average_return_cost
                + profile.average_storage_cost
            )
            break_even = fixed_unit_cost / max(0.05, 1 - variable_rates)
            recommended = fixed_unit_cost / max(0.05, 1 - variable_rates - business.target_margin)
            recommended = max(recommended, break_even)
            margin = net_profit / revenue if revenue > 0 else -1 if net_profit < 0 else 0
            avg_profit = net_profit / units_sold if units_sold else 0
            total_order_units = sum(o.quantity for o in orders) or 1
            return_rate = returned_count / total_order_units
            stock_value = product.unit_cost * product.stock_count
            daily_velocity = product.monthly_sales_velocity / 30 if product.monthly_sales_velocity else 0
            days_inventory = product.stock_count / daily_velocity if daily_velocity > 0 else None
            health = self._product_health_score(margin, return_rate, product.monthly_sales_velocity, days_inventory, avg_profit)
            status, reasons = self._product_status(margin, return_rate, days_inventory, net_profit, units_sold, health)
            max_discount = max(0.0, (product.sale_price - break_even) / product.sale_price * 100) if product.sale_price else 0
            safe_campaign_discount = min(max_discount, 12.0 if status == "grow" else 6.0 if status == "watch" else 0.0)
            next_step = self._product_next_step(status, product, recommended, max_discount)

            results.append(
                ProductProfitability(
                    sku=sku,
                    name=product.name,
                    category=product.category,
                    units_sold=units_sold,
                    revenue=round(revenue, 2),
                    total_cost=round(total_cost, 2),
                    net_profit=round(net_profit, 2),
                    margin=round(margin, 4),
                    return_rate=round(return_rate, 4),
                    avg_profit_per_unit=round(avg_profit, 2),
                    current_price=round(product.sale_price, 2),
                    break_even_price=round(break_even, 2),
                    recommended_price=round(recommended, 2),
                    max_safe_discount_percent=round(max_discount, 1),
                    stock_value=round(stock_value, 2),
                    days_of_inventory=round(days_inventory, 1) if days_inventory is not None else None,
                    health_score=round(health, 1),
                    status=status,
                    reasons=reasons,
                    commission_rate=round(profile.commission_rate, 4),
                    ad_rate=round(profile.ad_rate, 4),
                    payment_fee_rate=round(profile.payment_rate, 4),
                    average_shipping_cost=round(profile.average_shipping, 2),
                    average_return_cost=round(profile.average_return_cost, 2),
                    safe_campaign_discount_percent=round(safe_campaign_discount, 1),
                    next_step=next_step,
                )
            )

        # En kritik ürünler üstte; sonra en iyi büyütülebilecekler.
        status_weight = {"stop": 0, "liquidate": 1, "watch": 2, "grow": 3}
        return sorted(results, key=lambda p: (status_weight[p.status], p.net_profit))

    def _product_health_score(self, margin: float, return_rate: float, monthly_velocity: float, days_inventory: float | None, avg_profit: float) -> float:
        margin_score = clamp((margin + 0.05) / 0.35 * 100)
        return_score = clamp((0.25 - return_rate) / 0.25 * 100)
        velocity_score = clamp(monthly_velocity / 80 * 100)
        if days_inventory is None:
            inventory_score = 25
        elif days_inventory <= 45:
            inventory_score = 100
        elif days_inventory <= 90:
            inventory_score = 65
        elif days_inventory <= 150:
            inventory_score = 35
        else:
            inventory_score = 10
        profit_score = 100 if avg_profit > 80 else clamp(avg_profit / 80 * 100)
        return clamp(0.30 * margin_score + 0.20 * return_score + 0.20 * velocity_score + 0.15 * inventory_score + 0.15 * profit_score)

    def _product_status(self, margin: float, return_rate: float, days_inventory: float | None, net_profit: float, units_sold: int, health: float) -> tuple[str, list[str]]:
        reasons: list[str] = []
        if net_profit < 0:
            reasons.append("Net kâr negatif; satış arttıkça zarar büyüyebilir.")
        if margin < 0.05:
            reasons.append("Kâr marjı güvenli seviyenin altında.")
        if return_rate > 0.12:
            reasons.append("İade oranı yüksek; kârı eritiyor.")
        if days_inventory and days_inventory > 90:
            reasons.append("Stok devir hızı yavaş; nakit stokta kilitli.")
        if net_profit < 0 or (margin < 0.02 and units_sold > 0):
            return "stop", reasons or ["Ürün zarar sınırında."]
        if days_inventory and days_inventory > 120:
            return "liquidate", reasons or ["Stok eritme aksiyonu uygun."]
        if health >= 70 and margin >= 0.12 and return_rate < 0.08:
            return "grow", ["Kâr, satış hızı ve iade oranı sağlıklı."]
        return "watch", reasons or ["Yakından takip edilmeli."]

    def _product_next_step(self, status: str, product: Product, recommended: float, max_discount: float) -> str:
        if status == "stop":
            return f"Fiyatı en az {money(recommended)} seviyesine çek veya ürünü satıştan kaldır."
        if status == "liquidate":
            return f"Yeni stok alma; maksimum güvenli indirim %{max_discount:.1f}."
        if status == "grow":
            return "Reklam bütçesi ve görünürlük artırılabilir; stok kırılmasını önle."
        return "Kampanya açmadan önce kargo/komisyon sonrası marjı tekrar kontrol et."

    def _receivable_priorities(self, business: BusinessInput, cashflow: list[CashFlowPoint]) -> list[ReceivablePriority]:
        unpaid = [r for r in business.receivables if r.status == ReceivableStatus.UNPAID]
        max_amount = max((r.amount for r in unpaid), default=1)
        min_cash = min((p.closing_cash for p in cashflow), default=business.cash_balance)
        cash_gap = abs(min(0, min_cash))
        results: list[ReceivablePriority] = []
        for rec in unpaid:
            delay_days = max(0, (business.analysis_date - rec.due_date).days)
            amount_score = rec.amount / max_amount * 100
            delay_score = clamp(delay_days / 20 * 100)
            impact_score = clamp(rec.amount / max(1, cash_gap) * 100) if cash_gap > 0 else clamp(rec.amount / max(1, business.cash_balance) * 80)
            probability_score = rec.probability * 100
            score = clamp(0.35 * amount_score + 0.25 * delay_score + 0.25 * impact_score + 0.15 * probability_score)
            level = risk_level(score)
            impact = "Nakit açığını doğrudan kapatabilir" if cash_gap and rec.amount >= cash_gap else "Yaklaşan ödemeler için kasayı güçlendirir"
            if delay_days > 20:
                tone = "legal_warning"
            elif delay_days > 7:
                tone = "firm"
            elif delay_days > 0:
                tone = "balanced"
            else:
                tone = "soft"
            message = self.advice.collection_message(
                CollectionMessageRequest(
                    customer_name=rec.customer_name,
                    amount=rec.amount,
                    delay_days=delay_days,
                    tone=tone,
                )
            )
            results.append(
                ReceivablePriority(
                    id=rec.id,
                    customer_name=rec.customer_name,
                    amount=round(rec.amount, 2),
                    due_date=rec.due_date,
                    delay_days=delay_days,
                    probability=rec.probability,
                    priority_score=round(score, 1),
                    level=level,
                    impact=impact,
                    suggested_message=message,
                    collection_strategy=tone,
                )
            )
        return sorted(results, key=lambda r: r.priority_score, reverse=True)

    def _inventory_risks(self, business: BusinessInput, profitability: list[ProductProfitability]) -> list[InventoryRisk]:
        by_sku = {p.sku: p for p in profitability}
        total_cash_base = max(1, business.cash_balance)
        risks: list[InventoryRisk] = []
        for product in business.products:
            p = by_sku.get(product.sku)
            stock_value = product.unit_cost * product.stock_count
            days = p.days_of_inventory if p else None
            if days is None:
                level = RiskLevel.MEDIUM if product.stock_count > 0 else RiskLevel.LOW
                action = "Satış hızı verisi yok; stok yenilemeden önce satış geçmişi topla."
            elif days > 150:
                level = RiskLevel.CRITICAL
                action = "Stok eritme planı yap; ancak zarar ettiren indirimden kaçın."
            elif days > 90:
                level = RiskLevel.HIGH
                action = "Yeni stok alma; kontrollü paket teklif veya kanal değişimi değerlendir."
            elif days > 60:
                level = RiskLevel.MEDIUM
                action = "Stok seviyesi izlenmeli; yeni alım kararı satış hızına bağlanmalı."
            else:
                level = RiskLevel.LOW
                action = "Stok devir hızı sağlıklı."
            risks.append(
                InventoryRisk(
                    sku=product.sku,
                    name=product.name,
                    stock_count=product.stock_count,
                    stock_value=round(stock_value, 2),
                    days_of_inventory=days,
                    risk_level=level,
                    action=action,
                    locked_cash_ratio=round(stock_value / total_cash_base, 2),
                )
            )
        risk_weight = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3}
        return sorted(risks, key=lambda r: (risk_weight[r.risk_level], -r.stock_value))

    def _financial_snapshot(
        self,
        business: BusinessInput,
        profitability: list[ProductProfitability],
        receivables: list[ReceivablePriority],
        inventory: list[InventoryRisk],
    ) -> FinancialSnapshot:
        gross_sales = sum(o.sale_price * o.quantity for o in business.orders if not o.is_returned)
        product_cost = sum((next((p.unit_cost for p in business.products if p.sku == o.sku), 0) * o.quantity) for o in business.orders)
        paper_profit = gross_sales - product_cost
        real_net_profit = sum(p.net_profit for p in profitability)
        marketplace_costs = sum(o.commission + o.payment_fee for o in business.orders)
        shipping_and_packaging = sum(o.shipping_cost + o.packaging_cost for o in business.orders)
        return_costs = sum(o.return_cost for o in business.orders if o.is_returned)
        ad_spend = sum(o.ad_cost for o in business.orders)
        overdue = sum(r.amount for r in receivables if r.delay_days > 0)
        locked = sum(i.stock_value for i in inventory if i.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL})
        outgoing_14 = sum(p.amount for p in business.payables if 0 <= (p.due_date - business.analysis_date).days <= 14)
        incoming_14 = sum(r.amount * r.probability for r in business.receivables if r.status == ReceivableStatus.UNPAID and 0 <= (r.due_date - business.analysis_date).days <= 14)
        cash_conversion_gap = max(0, outgoing_14 - incoming_14 - business.cash_balance)
        return FinancialSnapshot(
            gross_sales=round(gross_sales, 2),
            paper_profit=round(paper_profit, 2),
            real_net_profit=round(real_net_profit, 2),
            marketplace_costs=round(marketplace_costs, 2),
            shipping_and_packaging_costs=round(shipping_and_packaging, 2),
            return_costs=round(return_costs, 2),
            ad_spend=round(ad_spend, 2),
            overdue_receivables=round(overdue, 2),
            locked_inventory_cash=round(locked, 2),
            cash_conversion_gap=round(cash_conversion_gap, 2),
            loss_making_products_count=sum(1 for p in profitability if p.net_profit < 0 or p.status == "stop"),
            dangerous_campaign_products_count=sum(1 for p in profitability if p.safe_campaign_discount_percent <= 0 and p.units_sold > 0),
        )

    def _risk_breakdown(
        self,
        business: BusinessInput,
        cashflow: list[CashFlowPoint],
        products: list[ProductProfitability],
        receivables: list[ReceivablePriority],
        inventory: list[InventoryRisk],
    ) -> RiskBreakdown:
        next_14 = cashflow[:14]
        out_14 = sum(p.expected_outflow for p in next_14)
        in_14 = sum(p.expected_inflow for p in next_14)
        min_cash = min((p.closing_cash for p in next_14), default=business.cash_balance)
        coverage = business.cash_balance + in_14
        pressure_base = out_14 / max(1, coverage) * 65
        gap_penalty = abs(min(0, min_cash)) / max(1, business.cash_balance) * 80
        payment_pressure = clamp(pressure_base + gap_penalty)

        overdue_amount = sum(r.amount for r in receivables if r.delay_days > 0)
        monthly_revenue = max(1.0, sum(o.sale_price * o.quantity for o in business.orders if not o.is_returned))
        receivable_risk = clamp(overdue_amount / monthly_revenue * 100)

        risky_products = [p for p in products if p.status in {"stop", "watch"} and (p.margin < 0.08 or p.net_profit < 0)]
        low_profit_product_risk = clamp(len(risky_products) / max(1, len(products)) * 100)

        stock_value = sum(i.stock_value for i in inventory if i.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL})
        stock_locked_risk = clamp(stock_value / max(1, business.cash_balance) * 75)

        returned_orders = sum(1 for o in business.orders if o.is_returned)
        revenue_uncertainty = clamp((returned_orders / max(1, len(business.orders)) * 70) + (len(receivables) / 10 * 30))

        total = clamp(
            0.35 * payment_pressure
            + 0.25 * receivable_risk
            + 0.20 * low_profit_product_risk
            + 0.10 * stock_locked_risk
            + 0.10 * revenue_uncertainty
        )
        return RiskBreakdown(
            payment_pressure=round(payment_pressure, 1),
            receivable_risk=round(receivable_risk, 1),
            low_profit_product_risk=round(low_profit_product_risk, 1),
            stock_locked_risk=round(stock_locked_risk, 1),
            revenue_uncertainty=round(revenue_uncertainty, 1),
            total_score=round(total, 1),
            level=risk_level(total),
        )

    def _actions(
        self,
        business: BusinessInput,
        cashflow: list[CashFlowPoint],
        products: list[ProductProfitability],
        receivables: list[ReceivablePriority],
        inventory: list[InventoryRisk],
        risk: RiskBreakdown,
    ) -> list[ActionItem]:
        actions: list[ActionItem] = []
        min_point = min(cashflow, key=lambda p: p.closing_cash)
        if min_point.closing_cash < 0:
            actions.append(ActionItem(
                title="Nakit açığı için acil kurtarma planı başlat",
                detail=f"{min_point.date.isoformat()} tarihinde kasa {money(min_point.closing_cash)} seviyesine düşebilir.",
                impact="Maaş, kira veya tedarikçi ödemesinde gecikmeyi önler.",
                priority="critical",
                category="cashflow",
            ))
        if receivables:
            r = receivables[0]
            actions.append(ActionItem(
                title=f"{r.customer_name} tahsilatını bugün takip et",
                detail=f"{money(r.amount)} tutarındaki alacak {r.delay_days} gün gecikmiş. {r.impact}.",
                impact="Kasayı hızlı güçlendirir ve kısa vadeli riski düşürür.",
                priority="critical" if r.level in {RiskLevel.HIGH, RiskLevel.CRITICAL} else "high",
                category="receivable",
            ))
        loss_products = [p for p in products if p.net_profit < 0 or p.status == "stop"]
        if loss_products:
            p = loss_products[0]
            actions.append(ActionItem(
                title=f"{p.name} fiyatını düzelt veya satışını durdur",
                detail=f"Mevcut fiyat {money(p.current_price)}, zarar etmeme fiyatı {money(p.break_even_price)}, önerilen fiyat {money(p.recommended_price)}.",
                impact="Satış arttıkça oluşan gizli zararı engeller.",
                priority="high",
                category="pricing",
            ))
        low_margin_campaign = [p for p in products if p.safe_campaign_discount_percent <= 0 and p.units_sold > 0]
        if low_margin_campaign:
            p = low_margin_campaign[0]
            actions.append(ActionItem(
                title=f"{p.name} için kampanya açma",
                detail=f"Güvenli indirim alanı yok. Bu üründe indirim, satış başına zarar doğurabilir.",
                impact="Yanlış kampanyayla büyüyen zararı engeller.",
                priority="high",
                category="marketplace",
            ))
        risky_inventory = [i for i in inventory if i.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}]
        if risky_inventory:
            i = risky_inventory[0]
            actions.append(ActionItem(
                title=f"{i.name} için yeni stok alma",
                detail=f"Stokta {money(i.stock_value)} nakit kilitli. {i.action}",
                impact="Nakit çevrim hızını korur.",
                priority="medium",
                category="inventory",
            ))
        grow_products = [p for p in products if p.status == "grow"]
        if grow_products:
            p = grow_products[0]
            actions.append(ActionItem(
                title=f"Kârlı ürün büyüt: {p.name}",
                detail=f"Kâr marjı %{p.margin*100:.1f}; iade oranı %{p.return_rate*100:.1f}. Reklam ve stok desteği verilebilir.",
                impact="Sınırlı nakdi en sağlıklı ürüne yönlendirir.",
                priority="medium",
                category="marketplace",
            ))
        if risk.total_score >= 60:
            actions.append(ActionItem(
                title="Yeni stok ve taksitli harcamayı geçici durdur",
                detail="Risk 60/100 üzerindeyken yeni stok alımı yalnızca hızlı dönen ve kârlı ürünlerle sınırlanmalı.",
                impact="Kriz gününden önce kasanın boşalmasını engeller.",
                priority="high",
                category="cashflow",
            ))
        actions.append(ActionItem(
            title="Veri kalitesini haftalık kontrol et",
            detail="Kargo, komisyon, reklam ve iade maliyetleri eksik girilirse ürün kârlılığı olduğundan iyi görünür.",
            impact="Yanlış fiyatlandırma kararlarını azaltır.",
            priority="low",
            category="data",
        ))
        priority_weight = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(actions, key=lambda a: priority_weight[a.priority])[:8]

    def _summary(
        self,
        cashflow: list[CashFlowPoint],
        risk: RiskBreakdown,
        actions: list[ActionItem],
        products: list[ProductProfitability],
        receivables: list[ReceivablePriority],
    ):
        min_point = min(cashflow, key=lambda p: p.closing_cash)
        cash_gap = abs(min(0, min_point.closing_cash))
        top_risks: list[str] = []
        if risk.payment_pressure > 55:
            top_risks.append("yaklaşan ödeme baskısı yüksek")
        if receivables and receivables[0].delay_days > 0:
            top_risks.append(f"{receivables[0].customer_name} tahsilatı gecikmiş")
        loss = [p for p in products if p.net_profit < 0 or p.status == "stop"]
        if loss:
            top_risks.append(f"{loss[0].name} satış başına zarar riski taşıyor")
        if risk.stock_locked_risk > 50:
            top_risks.append("stokta kilitlenen para yüksek")
        return ExecutiveSummary(
            headline=self.advice.headline(risk, cash_gap),
            narrative=self.advice.build_narrative(risk, top_risks),
            critical_day=min_point.date if cash_gap > 0 else None,
            minimum_cash=round(min_point.closing_cash, 2),
            cash_gap=round(cash_gap, 2),
            top_risks=top_risks,
            today_actions=[a.title for a in actions[:5]],
        )

    def _crisis_alert(
        self,
        cashflow: list[CashFlowPoint],
        snapshot: FinancialSnapshot,
        products: list[ProductProfitability],
        receivables: list[ReceivablePriority],
        inventory: list[InventoryRisk],
        actions: list[ActionItem],
    ) -> CrisisAlert:
        min_point = min(cashflow, key=lambda p: p.closing_cash)
        gap = abs(min(0, min_point.closing_cash))
        roots: list[str] = []
        if snapshot.cash_conversion_gap > 0:
            roots.append(f"Ödemeler, beklenen tahsilat ve mevcut kasadan {money(snapshot.cash_conversion_gap)} daha hızlı geliyor.")
        if receivables:
            roots.append(f"En kritik tahsilat: {receivables[0].customer_name} - {money(receivables[0].amount)}.")
        loss_products = [p for p in products if p.status == "stop" or p.net_profit < 0]
        if loss_products:
            roots.append(f"{loss_products[0].name} gerçek maliyet sonrası zarar sınırında.")
        risky_stock = [i for i in inventory if i.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}]
        if risky_stock:
            roots.append(f"{risky_stock[0].name} stokta {money(risky_stock[0].stock_value)} nakit kilitliyor.")
        if not roots:
            roots.append("Kritik bir nakit kırılması görünmüyor; risk düzenli izlenmeli.")
        survival = [a.title for a in actions[:5]]
        title = "Satış var ama kasa alarm veriyor" if gap > 0 else "Kasa pozitif; yine de marj ve stok kontrolü gerekli"
        desc = (
            f"En düşük kasa {min_point.date.isoformat()} tarihinde {money(min_point.closing_cash)} olabilir."
            if gap > 0 else
            f"30 günlük tahminde en düşük kasa {money(min_point.closing_cash)} seviyesinde kalıyor."
        )
        return CrisisAlert(
            title=title,
            description=desc,
            critical_day=min_point.date if gap > 0 else None,
            minimum_cash=round(min_point.closing_cash, 2),
            cash_gap=round(gap, 2),
            root_causes=roots,
            survival_plan=survival,
        )

    def _simulate_case(self, name: str, description: str, business: BusinessInput, risk_hint: float | None = None) -> ScenarioCase:
        points = self._build_cashflow(business)
        min_cash = min((p.closing_cash for p in points[:14]), default=business.cash_balance)
        day14_cash = points[13].closing_cash if len(points) >= 14 else points[-1].closing_cash
        gap = abs(min(0, min_cash))
        if risk_hint is None:
            risk_hint = clamp((gap / max(1, business.cash_balance) * 70) + (0 if min_cash > 0 else 20))
        interp = "Negatif kasa riski devam ediyor." if gap > 0 else "Bu senaryoda 14 günlük dönem pozitif kasayla geçilebilir."
        return ScenarioCase(
            name=name,
            description=description,
            day_14_cash=round(day14_cash, 2),
            minimum_cash=round(min_cash, 2),
            cash_gap=round(gap, 2),
            risk_score=round(risk_hint, 1),
            interpretation=interp,
        )

    def _scenario_suite(self, business: BusinessInput, products: list[ProductProfitability]) -> ScenarioSuite:
        base = self._simulate_case("Mevcut durum", "Hiçbir aksiyon alınmazsa 14 günlük nakit görünümü.", deepcopy(business))

        top_receivable_case = None
        unpaid = [r for r in business.receivables if r.status == ReceivableStatus.UNPAID]
        if unpaid:
            top = max(unpaid, key=lambda r: (business.analysis_date - r.due_date).days * 0.3 + r.amount / 1000)
            b = deepcopy(business)
            b.transactions.append(Transaction(
                id="SCN-COLLECT",
                date=b.analysis_date,
                description=f"Senaryo: {top.customer_name} tahsil edildi",
                amount=top.amount,
                type=TxType.INCOME,
                category="Senaryo",
            ))
            top_receivable_case = self._simulate_case(
                "En kritik alacak tahsil edildi",
                f"{top.customer_name} bugün {money(top.amount)} ödeme yaparsa.",
                b,
            )

        stock_frozen_case = None
        discretionary_keywords = ("stok", "tedarik", "malzeme", "ürün")
        b = deepcopy(business)
        postponed = 0.0
        for pay in b.payables:
            is_discretionary = not pay.is_fixed and any(k in (pay.category + ' ' + pay.vendor_name).lower() for k in discretionary_keywords)
            if is_discretionary and 0 <= (pay.due_date - b.analysis_date).days <= 14:
                postponed += pay.amount
                pay.due_date = pay.due_date + timedelta(days=14)
        if postponed > 0:
            stock_frozen_case = self._simulate_case(
                "Yeni stok alımı donduruldu",
                f"14 gün içinde {money(postponed)} stok/tedarik çıkışı ertelenirse.",
                b,
            )

        price_fix_case = None
        delta = self._price_fix_monthly_delta(products)
        if delta > 0:
            b = deepcopy(business)
            b.transactions.append(Transaction(
                id="SCN-PRICE-FIX",
                date=b.analysis_date + timedelta(days=14),
                description="Senaryo: zarar eden ürünlerde fiyat düzeltme etkisi",
                amount=delta * 14 / 30,
                type=TxType.INCOME,
                category="Senaryo",
            ))
            price_fix_case = self._simulate_case(
                "Zarar eden ürün fiyatları düzeltildi",
                f"Fiyat düzeltmeleri aylık yaklaşık {money(delta)} kâr etkisi yaratırsa.",
                b,
            )

        combined_case = None
        b = deepcopy(business)
        combined_desc: list[str] = []
        if unpaid:
            top = max(unpaid, key=lambda r: (business.analysis_date - r.due_date).days * 0.3 + r.amount / 1000)
            b.transactions.append(Transaction(
                id="SCN-COMBINED-COLLECT",
                date=b.analysis_date,
                description=f"Senaryo: {top.customer_name} tahsil edildi",
                amount=top.amount,
                type=TxType.INCOME,
                category="Senaryo",
            ))
            combined_desc.append(f"{top.customer_name} tahsilatı")
        for pay in b.payables:
            is_discretionary = not pay.is_fixed and any(k in (pay.category + ' ' + pay.vendor_name).lower() for k in discretionary_keywords)
            if is_discretionary and 0 <= (pay.due_date - b.analysis_date).days <= 14:
                pay.due_date = pay.due_date + timedelta(days=14)
                combined_desc.append("stok alımı erteleme")
        if delta > 0:
            b.transactions.append(Transaction(
                id="SCN-COMBINED-PRICE",
                date=b.analysis_date + timedelta(days=14),
                description="Senaryo: fiyat düzeltme etkisi",
                amount=delta * 14 / 30,
                type=TxType.INCOME,
                category="Senaryo",
            ))
            combined_desc.append("fiyat düzeltme")
        if combined_desc:
            combined_case = self._simulate_case(
                "Kurtarma paketi",
                " + ".join(combined_desc) + " birlikte uygulanırsa.",
                b,
            )

        return ScenarioSuite(
            base_case=base,
            top_receivable_collected=top_receivable_case,
            stock_purchase_frozen=stock_frozen_case,
            price_fix_applied=price_fix_case,
            combined_rescue=combined_case,
        )

    def _price_fix_monthly_delta(self, products: list[ProductProfitability]) -> float:
        delta = 0.0
        for p in products:
            if p.status == "stop" or p.margin < 0.05:
                old = p.avg_profit_per_unit
                new = max(0, p.recommended_price - p.current_price + old)
                delta += max(0, new - old) * max(0, p.units_sold)
        return delta

    def _data_quality_issues(self, business: BusinessInput, profitability: list[ProductProfitability]) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        product_skus = {p.sku for p in business.products}
        order_skus = {o.sku for o in business.orders}
        missing_products = sorted(order_skus - product_skus)
        if missing_products:
            issues.append(DataQualityIssue(
                severity=DataSeverity.CRITICAL,
                entity="orders/products",
                message=f"Siparişlerde ürün kartı olmayan SKU var: {', '.join(missing_products[:5])}.",
                recommendation="Ürün maliyeti bilinmeyen satışlarda kâr hesabı güvenilir olmaz; ürün kartlarını tamamla.",
            ))
        if any(o.shipping_cost == 0 for o in business.orders):
            issues.append(DataQualityIssue(
                severity=DataSeverity.WARNING,
                entity="orders",
                message="Bazı siparişlerde kargo maliyeti 0 görünüyor.",
                recommendation="Kargo maliyetini ürün bazında dağıt; aksi halde güvenli kampanya limiti yanlış çıkar.",
            ))
        if any(o.commission == 0 for o in business.orders):
            issues.append(DataQualityIssue(
                severity=DataSeverity.WARNING,
                entity="orders",
                message="Bazı siparişlerde pazaryeri komisyonu eksik.",
                recommendation="Komisyon oranı eksik ürünlerde net kâr olduğundan yüksek görünür.",
            ))
        if not business.receivables:
            issues.append(DataQualityIssue(
                severity=DataSeverity.INFO,
                entity="receivables",
                message="Açık alacak verisi girilmemiş.",
                recommendation="Tahsilat takibi eklenirse nakit açığı tahmini daha gerçekçi olur.",
            ))
        if not business.payables:
            issues.append(DataQualityIssue(
                severity=DataSeverity.INFO,
                entity="payables",
                message="Yaklaşan ödeme verisi girilmemiş.",
                recommendation="Kira, maaş, vergi, tedarikçi ve kargo ödemelerini yükle.",
            ))
        for p in profitability:
            if p.units_sold > 0 and p.average_shipping_cost == 0:
                issues.append(DataQualityIssue(
                    severity=DataSeverity.WARNING,
                    entity=f"product:{p.sku}",
                    message=f"{p.name} için ortalama kargo maliyeti 0.",
                    recommendation="Ürün kârlılığını netleştirmek için kargo maliyetini kontrol et.",
                ))
                break
        return issues[:8]

    def _daily_brief(self, summary, crisis: CrisisAlert, actions: list[ActionItem], scenario_suite: ScenarioSuite) -> DailyCFOBrief:
        priorities = [a.title for a in actions[:5]]
        forbidden: list[str] = []
        if crisis.cash_gap > 0:
            forbidden.append("Kritik güne kadar yeni stok veya plansız reklam harcaması yapma.")
        forbidden.append("Güvenli indirim yüzdesi 0 olan ürünlerde kampanya açma.")
        safe = ["Kârı kanıtlanmış ürünlere sınırlı reklam bütçesi aktar.", "Tahsilat mesajlarını ödeme etkisine göre sırala."]
        if scenario_suite.combined_rescue and scenario_suite.combined_rescue.cash_gap == 0:
            safe.append("Kurtarma paketini uygularsan 14 günlük negatif kasa riski kapanabilir.")
        morning = summary.headline + " " + (crisis.survival_plan[0] if crisis.survival_plan else "Bugün nakit, tahsilat ve ürün marjını kontrol et.")
        return DailyCFOBrief(
            morning_summary=morning,
            top_priorities=priorities,
            forbidden_actions=forbidden,
            safe_actions=safe,
        )

    def _integration_roadmap(self) -> list[IntegrationConnector]:
        return [
            IntegrationConnector(
                name="Pazaryeri CSV/API",
                category="marketplace",
                status="ready_for_csv",
                data_needed=["sipariş", "komisyon", "iade", "hakediş tarihi"],
                value="Gerçek kâr ve pazaryeri nakit gecikmesini otomatik hesaplar.",
            ),
            IntegrationConnector(
                name="Banka/Ekstre İçe Aktarma",
                category="banking",
                status="ready_for_csv",
                data_needed=["tarih", "açıklama", "tutar", "işlem tipi"],
                value="Kasa ve gider akışını manuel giriş olmadan oluşturur.",
            ),
            IntegrationConnector(
                name="E-fatura / Muhasebe",
                category="accounting",
                status="api_planned",
                data_needed=["fatura", "cari", "vade", "KDV"],
                value="Alacak/borç ve vergi riskini tek ekranda toplar.",
            ),
            IntegrationConnector(
                name="Kargo Faturası",
                category="shipping",
                status="ready_for_csv",
                data_needed=["desi", "ürün", "kargo bedeli", "iade kargo"],
                value="Ürün başına gizli kargo zararını ortaya çıkarır.",
            ),
            IntegrationConnector(
                name="WhatsApp/E-posta Tahsilat",
                category="communication",
                status="api_planned",
                data_needed=["müşteri", "tutar", "vade", "mesaj tonu"],
                value="Tahsilat aksiyonunu uygulama içinden başlatır.",
            ),
        ]

    def price_scenario(self, business: BusinessInput, sku: str, new_price: float) -> PriceScenarioResult:
        product = next((p for p in business.products if p.sku == sku), None)
        if product is None:
            raise ValueError(f"Product not found: {sku}")
        orders = [o for o in business.orders if o.sku == sku]
        profile = self._cost_profile(orders, product)
        old_profit, old_margin, break_even = self._unit_profit_at_price(product.sale_price, product, profile)
        new_profit, new_margin, _ = self._unit_profit_at_price(new_price, product, profile)
        price_change_pct = (new_price - product.sale_price) / max(1, product.sale_price)
        # Basit fiyat esnekliği modeli: fiyat artışının bir kısmı satış adedini düşürür.
        estimated_sales_change = clamp(-price_change_pct * 80, -35, 25)
        monthly_units = product.monthly_sales_velocity * (1 + estimated_sales_change / 100)
        old_monthly_profit = old_profit * product.monthly_sales_velocity
        new_monthly_profit = new_profit * monthly_units
        delta = new_monthly_profit - old_monthly_profit
        recommended = max(break_even, (product.unit_cost + profile.average_shipping + profile.average_packaging + profile.average_return_cost) / max(0.05, 1 - profile.commission_rate - profile.payment_rate - profile.ad_rate - business.target_margin))
        old_safe_discount = max(0, (product.sale_price - break_even) / max(1, product.sale_price) * 100)
        new_safe_discount = max(0, (new_price - break_even) / max(1, new_price) * 100)
        if delta > 0:
            interpretation = f"Fiyat değişimi satış adedini yaklaşık %{abs(estimated_sales_change):.1f} azaltabilir; buna rağmen aylık net kâr {money(delta)} artabilir."
        else:
            interpretation = f"Bu fiyat, tahmini satış etkisi sonrası aylık kârı {money(abs(delta))} azaltabilir. Daha kontrollü test önerilir."
        return PriceScenarioResult(
            sku=sku,
            old_price=round(product.sale_price, 2),
            new_price=round(new_price, 2),
            old_profit_per_unit=round(old_profit, 2),
            new_profit_per_unit=round(new_profit, 2),
            old_margin=round(old_margin, 4),
            new_margin=round(new_margin, 4),
            estimated_sales_change_percent=round(estimated_sales_change, 1),
            projected_monthly_profit_delta=round(delta, 2),
            break_even_price=round(break_even, 2),
            recommended_price=round(recommended, 2),
            old_safe_discount_percent=round(old_safe_discount, 1),
            new_safe_discount_percent=round(new_safe_discount, 1),
            interpretation=interpretation,
        )
