from __future__ import annotations

from app.core.constants import RISK_LABELS_TR
from app.domain.models import ActionItem, CollectionMessageRequest, RiskBreakdown


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    return f"{sign}{value:,.0f} TL".replace(",", ".")


class AdviceEngine:
    """Güvenli açıklama katmanı.

    Ürün stratejisi: hesaplama deterministik finans motorunda kalır; bu katman sayıları
    anlaşılır CFO diline çevirir. Gerçek LLM bağlanırsa da prompt'a yalnızca hesaplanmış
    metrikler verilmeli, para hesabı LLM'e yaptırılmamalıdır.
    """

    def headline(self, risk: RiskBreakdown, cash_gap: float) -> str:
        label = RISK_LABELS_TR[risk.level]
        if cash_gap > 0:
            return f"{label} risk: Önümüzdeki dönemde {money(cash_gap)} nakit açığı oluşabilir."
        return f"{label} risk: Nakit akışı izlenebilir seviyede."

    def build_narrative(self, risk: RiskBreakdown, top_risks: list[str]) -> str:
        intro = (
            "Bu analiz satış, tahsilat, yaklaşan ödeme, ürün kârlılığı, kampanya güvenliği ve stok verilerini birlikte değerlendirir. "
            f"Genel nakit risk skoru {risk.total_score:.0f}/100 seviyesinde."
        )
        if not top_risks:
            return intro + " Şu anda kritik bir darboğaz görünmüyor; ancak fiyat, stok ve tahsilat takibi sürdürülmeli."
        return intro + " Öne çıkan sebepler: " + "; ".join(top_risks[:4]) + "."

    def collection_message(self, req: CollectionMessageRequest) -> str:
        amount = money(req.amount)
        if req.tone == "soft":
            return (
                f"Merhaba, {amount} tutarındaki açık ödemeniz için uygun olduğunuzda bilgi rica ederiz. "
                "Ödeme tarihiyle ilgili destek olmamız gereken bir konu varsa yardımcı olabiliriz."
            )
        if req.tone == "legal_warning":
            return (
                f"Merhaba, {amount} tutarındaki ödemeniz vadesini aşmış görünüyor. "
                "Bugün içinde ödeme tarihi veya ödeme planı paylaşmanızı rica ederiz. "
                "Dönüş alamazsak cari hesabın resmi takip sürecine alınması gündeme gelecektir."
            )
        if req.tone == "firm":
            delay = f" {req.delay_days} gündür vadesi geçmiş" if req.delay_days else " vadesi gelmiş"
            return (
                f"Merhaba, {delay} durumda bulunan {amount} tutarındaki ödemeniz için bugün içinde dönüş rica ederiz. "
                "Uygun olmanız halinde ödeme planı konusunda yardımcı olabiliriz; ancak ödeme tarihini netleştirmemiz gerekiyor."
            )
        return (
            f"Merhaba, {amount} tutarındaki ödemenizin durumu hakkında bilgi rica ederiz. "
            "Mümkünse bugün içinde ödeme tarihi paylaşabilir misiniz? Gerekirse ödeme planı konusunda yardımcı olabiliriz."
        )

    def chat_answer(self, question: str, actions: list[ActionItem], risk: RiskBreakdown, cash_gap: float) -> str:
        q = question.lower()
        if any(word in q for word in ["maaş", "maas", "kira", "öde", "ode", "ay sonu", "çıkar", "cikar", "kasa", "nakit"]):
            if cash_gap > 0:
                return (
                    f"Mevcut veriye göre ödeme döneminde {money(cash_gap)} civarında açık riski var. "
                    "Öncelik geciken tahsilatları hızlandırmak, kampanya/indirimleri durdurmak ve düşük kârlı ürünlerde fiyat kararını düzeltmek olmalı. "
                    f"İlk aksiyon: {actions[0].title if actions else 'geciken alacakları kontrol et'}."
                )
            return "Mevcut tahminlerde maaş/kira döneminde negatif kasa görünmüyor. Yine de yeni stok ve kampanya kararlarını ürün kârlılığına göre vermelisin."
        if any(word in q for word in ["kampanya", "indirim", "fiyat"]):
            pricing_actions = [a for a in actions if a.category in {"pricing", "marketplace"}]
            if pricing_actions:
                return "Kampanya/fiyat tarafında kritik sinyal şu: " + pricing_actions[0].detail
            return "Kampanya açmadan önce ürün bazlı maksimum güvenli indirim yüzdesine bak. Marjı düşük ürünlerde satış artsa bile nakit zarar büyüyebilir."
        if any(word in q for word in ["en çok", "kazandır", "kâr", "ürün", "urun"]):
            pricing_actions = [a for a in actions if a.category in {"pricing", "marketplace"}]
            if pricing_actions:
                return "Ürün tarafında en kritik sinyal şu: " + pricing_actions[0].detail
            return "Ürün kârlılığı tarafında kritik bir zarar sinyali görünmüyor; en sağlıklı ürünleri büyüt, düşük marjlı ürünlerde kampanyadan kaçın."
        if any(word in q for word in ["risk", "tehlike", "bat", "sıkış", "nakit"]):
            return (
                f"Genel risk skoru {risk.total_score:.0f}/100. En yüksek bileşenler: "
                f"ödeme baskısı {risk.payment_pressure:.0f}, tahsilat riski {risk.receivable_risk:.0f}, "
                f"düşük kârlı ürün riski {risk.low_profit_product_risk:.0f}."
            )
        return (
            "Bu soruyu mevcut finans analizine göre şöyle özetlerim: önce nakit açığı yaratacak tarihleri, sonra geciken alacakları, "
            "son olarak zarar ettiren ürünleri kontrol etmelisin. Bugünkü en önemli aksiyonlar bölümündeki ilk 3 maddeyi uygularsan risk hızlı düşer."
        )
