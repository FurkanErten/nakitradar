from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.domain.models import AnalysisResult, BusinessInput, ChatRequest, ChatResponse, PriceScenarioResult
from app.services.advice_engine import AdviceEngine, money
from app.services.finance_engine import FinanceEngine


@dataclass(frozen=True)
class ChatToolResult:
    name: str
    payload: dict[str, Any]
    evidence: list[str]


@dataclass(frozen=True)
class LLMAnswer:
    text: str
    provider: str
    model: str | None


class AICFOService:
    """LLM destekli CFO sohbet katmanı.

    Üretim prensibi:
    - Net kâr, nakit akışı, risk, fiyat simülasyonu gibi hesapları LLM değil FinanceEngine yapar.
    - LLM yalnızca hesaplanmış JSON bağlamını açıklar ve aksiyon planına çevirir.
    - Varsayılan mod `auto`dur: Ollama local -> Gemini -> OpenAI -> deterministic local CFO fallback.
    - Böylece hackathon/demo internet, kota veya API key yüzünden çökmez.
    """

    SMALLTALK_WORDS = {
        "naber",
        "nasılsın",
        "nasilsin",
        "selam",
        "merhaba",
        "sa",
        "slm",
        "hello",
        "hi",
        "hey",
        "günaydın",
        "gunaydin",
        "iyi akşamlar",
        "iyi aksamlar",
    }

    def __init__(self, engine: FinanceEngine | None = None, advice: AdviceEngine | None = None):
        self.settings = get_settings()
        self.engine = engine or FinanceEngine()
        self.advice = advice or AdviceEngine()

    def status(self) -> dict[str, Any]:
        order = self._provider_order()
        ollama_reachable = None
        if "ollama" in order or self.settings.provider_mode in {"auto", "ollama"}:
            try:
                with httpx.Client(timeout=1.5) as client:
                    resp = client.get(f"{self.settings.ollama_base_url.rstrip('/')}/api/tags")
                    ollama_reachable = resp.status_code == 200
            except Exception:
                ollama_reachable = False

        provider_options = [
            {
                "key": "auto",
                "label": "Otomatik",
                "description": "Ollama → Gemini → OpenAI → Yerel CFO",
                "configured": bool(self._provider_order("auto")),
            },
            {
                "key": "ollama",
                "label": "Ollama Local",
                "description": f"Ücretsiz yerel model: {self.settings.ollama_model}",
                "configured": bool(ollama_reachable),
                "reachable": ollama_reachable,
            },
            {
                "key": "gemini",
                "label": "Gemini API",
                "description": f"Google Gemini: {self.settings.gemini_model}",
                "configured": bool(self.settings.gemini_api_key),
            },
            {
                "key": "openai",
                "label": "OpenAI GPT",
                "description": f"OpenAI: {self.settings.openai_model}",
                "configured": bool(self.settings.openai_api_key),
            },
            {
                "key": "local",
                "label": "Yerel CFO",
                "description": "API kullanmaz; kural tabanlı güvenli fallback",
                "configured": True,
            },
        ]

        if self.settings.provider_mode in {"disabled", "local"}:
            message = "Yerel CFO modu aktif; LLM devre dışı."
        elif order:
            labels = []
            for p in order:
                if p == "ollama":
                    labels.append(f"Ollama local ({self.settings.ollama_model})")
                elif p == "gemini":
                    labels.append(f"Gemini ({self.settings.gemini_model})")
                elif p == "openai":
                    labels.append(f"OpenAI ({self.settings.openai_model})")
            message = "AI sırası: " + " → ".join(labels) + " → Yerel CFO fallback"
        else:
            message = "LLM yapılandırması yok; yerel CFO fallback aktif."

        return {
            "enabled": bool(order),
            "provider": self.settings.provider_mode,
            "active_order": order,
            "model": self._model_for_provider(order[0]) if order else None,
            "ollama_base_url": self.settings.ollama_base_url,
            "ollama_reachable": ollama_reachable,
            "gemini_configured": bool(self.settings.gemini_api_key),
            "openai_configured": bool(self.settings.openai_api_key),
            "provider_options": provider_options,
            "message": message,
        }

    def answer(self, req: ChatRequest, business: BusinessInput, result: AnalysisResult) -> ChatResponse:
        suggestions = self._suggested_questions(result)
        provider_override = self._normalize_provider_override(req.llm_provider)

        if self._is_smalltalk(req.question):
            return self._answer_smalltalk(req.question, suggestions, provider_override)

        tool_result = self._run_relevant_tool(req.question, business, result)

        if not self._provider_order(provider_override):
            local_answer = self._local_answer(req.question, result, tool_result)
            return ChatResponse(
                answer=local_answer,
                provider="local",
                model=None,
                used_tools=[tool_result.name],
                evidence=tool_result.evidence,
                suggested_questions=suggestions,
            )

        try:
            llm_answer = self._call_best_llm(req.question, result, tool_result, provider_override)
            return ChatResponse(
                answer=llm_answer.text,
                provider=llm_answer.provider,  # type: ignore[arg-type]
                model=llm_answer.model,
                used_tools=[tool_result.name],
                evidence=tool_result.evidence,
                suggested_questions=suggestions,
            )
        except Exception as exc:  # pragma: no cover - network/API defensive fallback
            fallback = self._local_answer(req.question, result, tool_result)
            return ChatResponse(
                answer=(
                    fallback
                    + "\n\nNot: Harici LLM çağrısı başarısız olduğu için yerel CFO modu kullanıldı. "
                    + f"Hata özeti: {type(exc).__name__}"
                ),
                provider="error_fallback",
                model=self._first_configured_model(provider_override),
                used_tools=[tool_result.name],
                evidence=tool_result.evidence,
                suggested_questions=suggestions,
            )

    def _normalize_provider_override(self, provider: str | None) -> str | None:
        value = (provider or "").strip().lower()
        if not value or value == "auto":
            return "auto"
        if value in {"ollama", "gemini", "openai", "disabled", "local"}:
            return value
        return "auto"

    def _provider_order(self, provider_override: str | None = None) -> list[str]:
        mode = provider_override or self.settings.provider_mode
        if mode in {"disabled", "local"}:
            return []
        if mode == "ollama":
            return ["ollama"]
        if mode == "gemini":
            return ["gemini"] if self.settings.gemini_api_key else []
        if mode == "openai":
            return ["openai"] if self.settings.openai_api_key else []
        if mode == "auto":
            order = ["ollama"]
            if self.settings.gemini_api_key:
                order.append("gemini")
            if self.settings.openai_api_key:
                order.append("openai")
            return order
        return []

    def _model_for_provider(self, provider: str | None) -> str | None:
        if provider == "ollama":
            return self.settings.ollama_model
        if provider == "gemini":
            return self.settings.gemini_model
        if provider == "openai":
            return self.settings.openai_model
        return None

    def _first_configured_model(self, provider_override: str | None = None) -> str | None:
        order = self._provider_order(provider_override)
        if not order:
            return None
        return self._model_for_provider(order[0])

    def _is_smalltalk(self, message: str) -> bool:
        text = " ".join(message.lower().strip().split())
        if text in self.SMALLTALK_WORDS:
            return True
        if len(text.split()) <= 3 and any(word in text for word in self.SMALLTALK_WORDS):
            return True
        return False

    def _answer_smalltalk(self, question: str, suggestions: list[str], provider_override: str | None = None) -> ChatResponse:
        prompt = (
            "Kullanıcı finans dışı kısa bir selamlama yaptı. "
            "Türkçe, samimi ama profesyonel şekilde cevap ver. "
            "Kendini NakitRadar AI finans asistanı olarak tanıt ve kullanıcının sorabileceği 2-3 finans sorusu örneği ver. "
            "Nakit skoru, ürün, müşteri, tutar gibi finans verisi uydurma."
        )
        if self._provider_order(provider_override):
            try:
                llm = self._call_best_llm_general(prompt, question, provider_override)
                return ChatResponse(
                    answer=llm.text,
                    provider=llm.provider,  # type: ignore[arg-type]
                    model=llm.model,
                    used_tools=["smalltalk"],
                    evidence=[],
                    suggested_questions=suggestions,
                )
            except Exception:
                pass
        return ChatResponse(
            answer=(
                "Merhaba, ben NakitRadar AI finans asistanıyım. "
                "Nakit akışı, zarar ettiren ürünler, tahsilat önceliği ve fiyatlandırma kararları hakkında soru sorabilirsin.\n\n"
                "Örnek sorular:\n"
                "- Ay sonunu çıkarabilir miyim?\n"
                "- Hangi ürün zarar ettiriyor?\n"
                "- Bugün kimden tahsilat istemeliyim?"
            ),
            provider="local",
            model=None,
            used_tools=["smalltalk"],
            evidence=[],
            suggested_questions=suggestions,
        )

    def _run_relevant_tool(self, question: str, business: BusinessInput, result: AnalysisResult) -> ChatToolResult:
        q = question.lower()
        price_match = self._extract_price_question(question, result)
        if price_match:
            sku, new_price = price_match
            try:
                scenario = self.engine.price_scenario(business, sku, new_price)
                return ChatToolResult(
                    name="simulate_price_change",
                    payload=self._price_payload(scenario),
                    evidence=[
                        f"Ürün: {scenario.sku}",
                        f"Eski fiyat: {money(scenario.old_price)}",
                        f"Yeni fiyat: {money(scenario.new_price)}",
                        f"Aylık kâr etkisi: {money(scenario.projected_monthly_profit_delta)}",
                    ],
                )
            except Exception:
                pass

        if any(w in q for w in ["ürün", "urun", "kâr", "kar", "kazandır", "zarar", "fiyat", "indirim", "kampanya"]):
            products = result.product_profitability[: self.settings.ai_max_context_products]
            return ChatToolResult(
                name="get_product_profitability",
                payload={
                    "products": [
                        {
                            "sku": p.sku,
                            "name": p.name,
                            "status": p.status,
                            "net_profit": p.net_profit,
                            "margin": p.margin,
                            "current_price": p.current_price,
                            "break_even_price": p.break_even_price,
                            "recommended_price": p.recommended_price,
                            "safe_discount_percent": p.safe_campaign_discount_percent,
                            "next_step": p.next_step,
                            "reasons": p.reasons[:2],
                        }
                        for p in products
                    ]
                },
                evidence=[f"{p.name}: net kâr {money(p.net_profit)}, önerilen fiyat {money(p.recommended_price)}" for p in products[:4]],
            )

        if any(w in q for w in ["tahsil", "müşteri", "musteri", "alacak", "kimden", "para iste"]):
            recs = result.receivable_priorities[:5]
            return ChatToolResult(
                name="get_receivable_priorities",
                payload={
                    "receivables": [
                        {
                            "customer_name": r.customer_name,
                            "amount": r.amount,
                            "delay_days": r.delay_days,
                            "priority_score": r.priority_score,
                            "impact": r.impact,
                            "message": r.suggested_message,
                        }
                        for r in recs
                    ]
                },
                evidence=[f"{r.customer_name}: {money(r.amount)}, {r.delay_days} gün gecikme" for r in recs[:4]],
            )

        if any(w in q for w in ["stok", "depo", "kilit", "envanter"]):
            inv = result.inventory_risks[:6]
            return ChatToolResult(
                name="get_inventory_risk",
                payload={
                    "inventory": [
                        {
                            "sku": i.sku,
                            "name": i.name,
                            "stock_value": i.stock_value,
                            "days_of_inventory": i.days_of_inventory,
                            "risk_level": i.risk_level.value,
                            "action": i.action,
                        }
                        for i in inv
                    ]
                },
                evidence=[f"{i.name}: stokta {money(i.stock_value)}, risk {i.risk_level.value}" for i in inv[:4]],
            )

        if any(w in q for w in ["bugün", "bugun", "ne yap", "aksiyon", "plan", "kurtar"]):
            return ChatToolResult(
                name="generate_today_actions",
                payload={
                    "top_priorities": result.daily_brief.top_priorities,
                    "forbidden_actions": result.daily_brief.forbidden_actions,
                    "safe_actions": result.daily_brief.safe_actions,
                    "actions": [a.model_dump() for a in result.actions[: self.settings.ai_max_context_actions]],
                },
                evidence=result.summary.today_actions[:5],
            )

        return ChatToolResult(
            name="get_cashflow_forecast",
            payload={
                "headline": result.summary.headline,
                "risk_score": result.risk.total_score,
                "risk_level": result.risk.level.value,
                "critical_day": str(result.summary.critical_day) if result.summary.critical_day else None,
                "minimum_cash": result.summary.minimum_cash,
                "cash_gap": result.summary.cash_gap,
                "top_risks": result.summary.top_risks,
                "cashflow_14_days": [p.model_dump(mode="json") for p in result.cashflow[:14]],
                "scenario_suite": result.scenario_suite.model_dump(mode="json"),
            },
            evidence=[
                f"Risk skoru: {result.risk.total_score:.0f}/100",
                f"Minimum kasa: {money(result.summary.minimum_cash)}",
                f"Nakit açığı: {money(result.summary.cash_gap)}",
            ],
        )

    def _extract_price_question(self, question: str, result: AnalysisResult) -> tuple[str, float] | None:
        numbers = re.findall(r"(?:\d+[\.,]?\d*)", question.replace("₺", " "))
        if not numbers:
            return None
        price = float(numbers[-1].replace(",", "."))
        if price < 10:
            return None
        q = question.lower()
        for p in result.product_profitability:
            if p.sku.lower() in q or p.name.lower() in q:
                return p.sku, price
        critical = next((p for p in result.product_profitability if p.status == "stop"), None)
        if critical and any(w in q for w in ["fiyat", "yapsam", "çıkar", "cikar", "artır", "artir"]):
            return critical.sku, price
        return None

    def _price_payload(self, scenario: PriceScenarioResult) -> dict[str, Any]:
        return scenario.model_dump()

    def _context_payload(self, result: AnalysisResult, tool_result: ChatToolResult) -> dict[str, Any]:
        return {
            "business": result.profile.model_dump(mode="json"),
            "analysis_date": str(result.analysis_date),
            "executive_summary": result.summary.model_dump(mode="json"),
            "financial_snapshot": result.financial_snapshot.model_dump(mode="json"),
            "risk": result.risk.model_dump(mode="json"),
            "selected_tool": tool_result.name,
            "tool_result": tool_result.payload,
            "actions": [a.model_dump(mode="json") for a in result.actions[: self.settings.ai_max_context_actions]],
            "data_quality": [d.model_dump(mode="json") for d in result.data_quality_issues[:5]],
        }

    def _system_prompt(self) -> str:
        return (
            "Sen NakitRadar AI içindeki Türkçe konuşan AI CFO asistansın. "
            "Kullanıcı KOBİ/e-ticaret satıcısıdır. Hesap uydurma; yalnızca verilen JSON bağlamındaki finans motoru sonuçlarına dayan. "
            "Eksik veri varsa açıkça söyle. Kullanıcıya kısa, net ve aksiyon odaklı cevap ver. "
            "Cevabı şu başlıklarla ver: Kısa Cevap, Neden, Finansal Etki, Önerilen Aksiyon, Risk Notu. "
            "Hukuki/finansal kesin taahhüt verme; bu bir karar destek analizidir. "
            "Tablo kullanma, 3-5 maddelik net liste kullan."
        )

    def _user_prompt(self, question: str, result: AnalysisResult, tool_result: ChatToolResult) -> str:
        context = self._context_payload(result, tool_result)
        return (
            "Kullanıcı sorusu:\n"
            f"{question}\n\n"
            "Finans motoru bağlamı JSON:\n"
            f"{json.dumps(context, ensure_ascii=False, indent=2)}"
        )

    def _call_best_llm(self, question: str, result: AnalysisResult, tool_result: ChatToolResult, provider_override: str | None = None) -> LLMAnswer:
        system_prompt = self._system_prompt()
        user_prompt = self._user_prompt(question, result, tool_result)
        return self._call_best_llm_general(system_prompt, user_prompt, provider_override)

    def _call_best_llm_general(self, system_prompt: str, user_prompt: str, provider_override: str | None = None) -> LLMAnswer:
        errors: list[str] = []
        for provider in self._provider_order(provider_override):
            try:
                if provider == "ollama":
                    return LLMAnswer(
                        text=self._call_ollama(system_prompt, user_prompt),
                        provider="ollama",
                        model=self.settings.ollama_model,
                    )
                if provider == "gemini":
                    return LLMAnswer(
                        text=self._call_gemini(system_prompt, user_prompt),
                        provider="gemini",
                        model=self.settings.gemini_model,
                    )
                if provider == "openai":
                    return LLMAnswer(
                        text=self._call_openai(system_prompt, user_prompt),
                        provider="openai",
                        model=self.settings.openai_model,
                    )
            except Exception as exc:
                errors.append(f"{provider}: {type(exc).__name__}")
                continue
        raise RuntimeError("LLM providers failed: " + ", ".join(errors))

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("google-genai package is not installed") from exc

        client = genai.Client(api_key=self.settings.gemini_api_key)
        response = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2,
            ),
        )
        text = getattr(response, "text", None)
        if text and text.strip():
            return text.strip()
        chunks: list[str] = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    chunks.append(part_text)
        text = "\n".join(chunks).strip()
        if not text:
            raise RuntimeError("Gemini returned empty response")
        return text

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("openai package is not installed") from exc

        client = OpenAI(api_key=self.settings.openai_api_key, timeout=self.settings.openai_timeout_seconds)
        response = client.responses.create(
            model=self.settings.openai_model,
            instructions=system_prompt,
            input=user_prompt,
        )
        text = getattr(response, "output_text", None)
        if text:
            return text.strip()
        chunks: list[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                maybe_text = getattr(content, "text", None)
                if maybe_text:
                    chunks.append(maybe_text)
        return "\n".join(chunks).strip()

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": 0.2,
                "num_ctx": 8192,
            },
        }
        with httpx.Client(timeout=self.settings.ollama_timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        message = data.get("message") or {}
        text = message.get("content") or data.get("response") or ""
        if not text.strip():
            raise RuntimeError("Ollama returned empty response")
        return text.strip()

    def _local_answer(self, question: str, result: AnalysisResult, tool_result: ChatToolResult) -> str:
        base = self.advice.chat_answer(question, result.actions, result.risk, result.summary.cash_gap)
        lines = ["Kısa Cevap:", base, "", "Kanıt:"]
        lines.extend([f"- {e}" for e in tool_result.evidence[:5]])
        if result.actions:
            lines.extend(["", "Önerilen Aksiyon:"])
            lines.extend([f"- {a.title}: {a.impact}" for a in result.actions[:3]])
        return "\n".join(lines)

    def _suggested_questions(self, result: AnalysisResult) -> list[str]:
        first_product = result.product_profitability[0].name if result.product_profitability else "zarar eden ürün"
        first_rec = result.receivable_priorities[0].customer_name if result.receivable_priorities else "en kritik müşteri"
        return [
            "Ay sonunu çıkarabilir miyim?",
            f"{first_product} için fiyatı artırırsam ne olur?",
            f"{first_rec} için nasıl tahsilat mesajı atmalıyım?",
            "Bugün öncelikli 3 aksiyonum ne?",
            "Hangi ürünlere kampanya yapmamalıyım?",
        ]
