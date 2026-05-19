import { FormEvent, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Bot, CheckCircle2, ChevronRight, FileSpreadsheet, Loader2, MessageSquareText, RefreshCw, TrendingUp, UploadCloud, WalletCards } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { AIProvider, AIStatus, AnalysisResult, ChatResponse, DatasetInfo, PriceScenarioResult, ProductProfitability, ReceivablePriority } from './lib/types'
import { askChat, getAIStatus, getDatasets, getDemoAnalysis, runPriceScenario, uploadAnalysis } from './lib/api'

const money = (value: number) => `${value < 0 ? '-' : ''}${Math.abs(value).toLocaleString('tr-TR', { maximumFractionDigits: 0 })} TL`
const pct = (value: number) => `%${(value * 100).toLocaleString('tr-TR', { maximumFractionDigits: 1 })}`
const riskLabel: Record<string, string> = { low: 'Düşük', medium: 'Orta', high: 'Yüksek', critical: 'Kritik' }
const productLabel: Record<string, string> = { grow: 'Büyüt', watch: 'İzle', liquidate: 'Erit', stop: 'Durdur' }
const aiProviderLabel: Record<string, string> = { auto: 'Otomatik', ollama: 'Ollama Local', gemini: 'Gemini API', openai: 'OpenAI GPT', local: 'Yerel CFO' }

type Tab = 'overview' | 'products' | 'receivables' | 'ai' | 'upload'

function RiskPill({ level }: { level: string }) {
  return <span className={`pill ${level}`}>{riskLabel[level] || level}</span>
}

function Metric({ title, value, note }: { title: string; value: string; note?: string }) {
  return (
    <div className="metric">
      <span>{title}</span>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </div>
  )
}

function CashChart({ result }: { result: AnalysisResult }) {
  const data = result.cashflow.slice(0, 30).map((p) => ({ date: p.date.slice(5), kasa: p.closing_cash }))
  return (
    <section className="panel panelWide">
      <div className="panelTitle">
        <div>
          <span className="eyebrow">30 günlük tahmin</span>
          <h2>Nakit akışı</h2>
        </div>
        <RiskPill level={result.risk.level} />
      </div>
      <div className="chartBox">
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis tickFormatter={(v) => `${Math.round(Number(v) / 1000)}k`} />
            <Tooltip formatter={(v: unknown) => money(Number(v ?? 0))} />
            <Area dataKey="kasa" type="monotone" strokeWidth={3} fillOpacity={0.18} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

function Overview({ result }: { result: AnalysisResult }) {
  const fs = result.financial_snapshot
  return (
    <div className="viewGrid">
      <section className="panel heroPanel">
        <span className="eyebrow">Satış var, para yok analizi</span>
        <h1>{result.summary.headline}</h1>
        <p>{result.summary.narrative}</p>
        <div className="metrics four">
          <Metric title="Risk skoru" value={`${result.risk.total_score.toFixed(0)}/100`} note={riskLabel[result.risk.level]} />
          <Metric title="Nakit açığı" value={money(result.summary.cash_gap)} note="Tahmini minimum açık" />
          <Metric title="Gerçek net kâr" value={money(fs.real_net_profit)} note={`Kağıt kâr: ${money(fs.paper_profit)}`} />
          <Metric title="Stokta kilitli" value={money(fs.locked_inventory_cash)} note={`${fs.loss_making_products_count} riskli ürün`} />
        </div>
      </section>

      <CashChart result={result} />

      <section className="panel">
        <div className="panelTitle">
          <div>
            <span className="eyebrow">Bugün</span>
            <h2>Öncelikli aksiyonlar</h2>
          </div>
          <CheckCircle2 />
        </div>
        <div className="actionList">
          {result.actions.slice(0, 5).map((a, index) => (
            <article className={`action ${a.priority}`} key={`${a.title}-${index}`}>
              <b>{index + 1}</b>
              <div>
                <strong>{a.title}</strong>
                <p>{a.detail}</p>
                <small>{a.impact}</small>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panelTitle">
          <div>
            <span className="eyebrow">Kriz sebebi</span>
            <h2>Kök nedenler</h2>
          </div>
          <AlertTriangle />
        </div>
        <ul className="cleanList">
          {result.crisis_alert.root_causes.map((x) => <li key={x}>{x}</li>)}
        </ul>
        <div className="divider" />
        <h3>Kurtarma planı</h3>
        <ol className="cleanList numbered">
          {result.crisis_alert.survival_plan.map((x) => <li key={x}>{x}</li>)}
        </ol>
      </section>
    </div>
  )
}

function ProductTable({ products }: { products: ProductProfitability[] }) {
  return (
    <section className="panel panelWide">
      <div className="panelTitle">
        <div>
          <span className="eyebrow">Ürün bazlı gerçek kâr</span>
          <h2>Zarar ettiren satış dedektörü</h2>
        </div>
      </div>
      <div className="tableWrap">
        <table className="dataTable">
          <thead>
            <tr>
              <th>Ürün</th>
              <th>Durum</th>
              <th>Net Kâr</th>
              <th>Marj</th>
              <th>Fiyat</th>
              <th>Öneri</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.sku}>
                <td>
                  <strong>{p.name}</strong>
                  <small>{p.sku} · {p.category}</small>
                </td>
                <td><span className={`status ${p.status}`}>{productLabel[p.status]}</span></td>
                <td className={p.net_profit < 0 ? 'negative' : 'positive'}>{money(p.net_profit)}</td>
                <td>{pct(p.margin)}</td>
                <td>
                  <span>{money(p.current_price)}</span>
                  <small>Başabaş: {money(p.break_even_price)}</small>
                </td>
                <td>
                  <strong>{money(p.recommended_price)}</strong>
                  <small>{p.next_step}</small>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function ProductsView({ result, datasetKey }: { result: AnalysisResult; datasetKey: string }) {
  const defaultSku = result.product_profitability[0]?.sku || ''
  const [sku, setSku] = useState(defaultSku)
  const [price, setPrice] = useState(result.product_profitability[0]?.recommended_price || 0)
  const [scenario, setScenario] = useState<PriceScenarioResult | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const p = result.product_profitability[0]
    if (p) {
      setSku(p.sku)
      setPrice(Math.round(p.recommended_price))
      setScenario(null)
    }
  }, [result])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    try { setScenario(await runPriceScenario(sku, Number(price), datasetKey)) }
    finally { setLoading(false) }
  }

  return (
    <div className="viewGrid">
      <ProductTable products={result.product_profitability} />
      <section className="panel">
        <span className="eyebrow">What-if</span>
        <h2>Fiyat değişirse ne olur?</h2>
        <form className="compactForm" onSubmit={submit}>
          <label>Ürün
            <select value={sku} onChange={(e) => setSku(e.target.value)}>
              {result.product_profitability.map((p) => <option key={p.sku} value={p.sku}>{p.name}</option>)}
            </select>
          </label>
          <label>Yeni fiyat
            <input type="number" value={price} onChange={(e) => setPrice(Number(e.target.value))} min={1} />
          </label>
          <button type="submit" disabled={loading}>{loading ? <Loader2 className="spin" /> : <TrendingUp />} Simüle et</button>
        </form>
        {scenario && (
          <div className="resultBox">
            <strong>{scenario.sku} senaryosu</strong>
            <p>{scenario.interpretation}</p>
            <div className="metrics twoCols">
              <Metric title="Eski birim kâr" value={money(scenario.old_profit_per_unit)} />
              <Metric title="Yeni birim kâr" value={money(scenario.new_profit_per_unit)} />
              <Metric title="Aylık etki" value={money(scenario.projected_monthly_profit_delta)} />
              <Metric title="Yeni marj" value={pct(scenario.new_margin)} />
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

function ReceivablesView({ receivables }: { receivables: ReceivablePriority[] }) {
  return (
    <section className="panel panelWide">
      <div className="panelTitle">
        <div>
          <span className="eyebrow">Tahsilat önceliği</span>
          <h2>Bugün kimden para istenmeli?</h2>
        </div>
      </div>
      <div className="tableWrap">
        <table className="dataTable">
          <thead>
            <tr>
              <th>Müşteri</th>
              <th>Tutar</th>
              <th>Gecikme</th>
              <th>Öncelik</th>
              <th>Etki</th>
              <th>Mesaj taslağı</th>
            </tr>
          </thead>
          <tbody>
            {receivables.map((r) => (
              <tr key={r.id}>
                <td><strong>{r.customer_name}</strong><small>Vade: {r.due_date}</small></td>
                <td>{money(r.amount)}</td>
                <td>{r.delay_days} gün</td>
                <td><RiskPill level={r.level} /></td>
                <td>{r.impact}</td>
                <td><small className="messagePreview">{r.suggested_message}</small></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function AIChat({ result, datasetKey, aiProvider, setAIProvider }: { result: AnalysisResult; datasetKey: string; aiProvider: AIProvider; setAIProvider: (provider: AIProvider) => void }) {
  const [question, setQuestion] = useState('Ay sonunu çıkarabilir miyim?')
  const [answer, setAnswer] = useState<ChatResponse | null>(null)
  const [aiStatus, setAIStatus] = useState<AIStatus | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => { getAIStatus().then(setAIStatus).catch(() => setAIStatus(null)) }, [])

  async function submit(e?: FormEvent) {
    e?.preventDefault()
    if (!question.trim()) return
    setLoading(true)
    try { setAnswer(await askChat(question, datasetKey, aiProvider)) }
    finally { setLoading(false) }
  }

  const quickQuestions = useMemo(() => answer?.suggested_questions?.length ? answer.suggested_questions : [
    'Bugün öncelikli 3 aksiyonum ne?',
    'Hangi ürün zarar ettiriyor?',
    'Kampanya yaparsam risk artar mı?',
    'Kimden önce tahsilat istemeliyim?',
  ], [answer])

  return (
    <div className="viewGrid">
      <section className="panel aiPanel">
        <div className="panelTitle">
          <div>
            <span className="eyebrow">AI Finans Sohbeti</span>
            <h2>Seçilebilir AI sağlayıcı + finans motoru</h2>
          </div>
          <Bot />
        </div>
        <div className="aiControls">
          <label>AI sağlayıcı
            <select value={aiProvider} onChange={(e) => { setAIProvider(e.target.value as AIProvider); setAnswer(null) }}>
              <option value="auto">Otomatik</option>
              <option value="ollama">Ollama Local</option>
              <option value="gemini">Gemini API</option>
              <option value="openai">OpenAI GPT</option>
              <option value="local">Yerel CFO</option>
            </select>
          </label>
          <div className="aiStatus">
            <span className={aiStatus?.enabled || aiProvider === 'local' ? 'dot on' : 'dot'} />
            <strong>{aiProviderLabel[aiProvider]}</strong>
            <small>{aiStatus?.message || 'AI durumu okunuyor'}</small>
          </div>
        </div>
        <form className="chatForm" onSubmit={submit}>
          <textarea value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Örn: Ürün C fiyatını 469 TL yaparsam ne olur?" />
          <button type="submit" disabled={loading}>{loading ? <Loader2 className="spin" /> : <MessageSquareText />} Sor</button>
        </form>
        <div className="quickQuestions">
          {quickQuestions.map((q) => (
            <button key={q} type="button" onClick={() => { setQuestion(q); setAnswer(null) }}>{q}</button>
          ))}
        </div>
        {answer && (
          <article className="answerBox">
            <div className="answerMeta">
              <span>{answer.provider === 'openai' ? 'OpenAI GPT cevabı' : answer.provider === 'gemini' ? 'Gemini API cevabı' : answer.provider === 'ollama' ? 'Ollama local AI cevabı' : answer.provider === 'error_fallback' ? 'Fallback CFO modu' : 'Yerel CFO modu'}</span>
              <span>{answer.used_tools.join(', ')}</span>
            </div>
            <pre>{answer.answer}</pre>
            {!!answer.evidence.length && <div className="evidence"><strong>Kanıt:</strong>{answer.evidence.map((e) => <small key={e}>{e}</small>)}</div>}
          </article>
        )}
      </section>
      <section className="panel">
        <span className="eyebrow">Bağlam</span>
        <h2>AI hangi veriye bakıyor?</h2>
        <ul className="cleanList">
          <li>Risk skoru: {result.risk.total_score.toFixed(0)}/100</li>
          <li>Nakit açığı: {money(result.summary.cash_gap)}</li>
          <li>Zarar riski: {result.financial_snapshot.loss_making_products_count} ürün</li>
          <li>Geciken alacak: {money(result.financial_snapshot.overdue_receivables)}</li>
          <li>Stokta kilitli para: {money(result.financial_snapshot.locked_inventory_cash)}</li>
        </ul>
      </section>
    </div>
  )
}

function UploadView({ onUploaded }: { onUploaded: (result: AnalysisResult) => void }) {
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError('')
    setLoading(true)
    const form = new FormData(e.currentTarget)
    try { onUploaded(await uploadAnalysis(form)) }
    catch (err) { setError(err instanceof Error ? err.message : 'Yükleme hatası') }
    finally { setLoading(false) }
  }

  return (
    <section className="panel panelWide">
      <div className="panelTitle">
        <div>
          <span className="eyebrow">CSV / Excel import</span>
          <h2>Kendi işletme verini yükle</h2>
        </div>
        <UploadCloud />
      </div>
      <form className="uploadGrid" onSubmit={submit}>
        <label>İşletme adı<input name="business_name" defaultValue="Yüklenen İşletme" /></label>
        <label>Mevcut kasa<input name="cash_balance" type="number" defaultValue={64000} min={0} /></label>
        <label>Ürünler<input name="products_file" type="file" accept=".csv,.xlsx,.xls" /></label>
        <label>Siparişler<input name="orders_file" type="file" accept=".csv,.xlsx,.xls" /></label>
        <label>Gelir/Gider<input name="transactions_file" type="file" accept=".csv,.xlsx,.xls" /></label>
        <label>Alacaklar<input name="receivables_file" type="file" accept=".csv,.xlsx,.xls" /></label>
        <label>Borçlar<input name="payables_file" type="file" accept=".csv,.xlsx,.xls" /></label>
        <button type="submit" disabled={loading}>{loading ? <Loader2 className="spin" /> : <FileSpreadsheet />} Analiz et</button>
      </form>
      {error && <div className="errorBox">{error}</div>}
    </section>
  )
}

export default function App() {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [datasets, setDatasets] = useState<DatasetInfo[]>([])
  const [datasetKey, setDatasetKey] = useState('default')
  const [aiProvider, setAIProvider] = useState<AIProvider>(() => (localStorage.getItem('nakitradar-ai-provider') as AIProvider) || 'auto')
  const [tab, setTab] = useState<Tab>('overview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadDataset(key = datasetKey) {
    setLoading(true)
    setError('')
    try { setResult(await getDemoAnalysis(key)) }
    catch (err) { setError(err instanceof Error ? err.message : 'Analiz yüklenemedi') }
    finally { setLoading(false) }
  }

  useEffect(() => {
    getDatasets().then(setDatasets).catch(() => setDatasets([]))
    loadDataset('default')
  }, [])

  useEffect(() => {
    localStorage.setItem('nakitradar-ai-provider', aiProvider)
  }, [aiProvider])

  async function changeDataset(key: string) {
    setDatasetKey(key)
    await loadDataset(key)
  }

  if (loading && !result) {
    return <main className="center"><Loader2 className="spin" /><p>Finans motoru başlatılıyor...</p></main>
  }

  if (error && !result) {
    return <main className="center"><AlertTriangle /><h2>Backend bağlantısı yok</h2><p>{error}</p><small>Backend: python -m uvicorn app.main:app --reload --port 8000</small></main>
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand">
          <WalletCards />
          <div>
            <strong>NakitRadar AI</strong>
            <span>KOBİ ve e-ticaret için mini CFO</span>
          </div>
        </div>
        <div className="topControls">
          <select value={datasetKey} onChange={(e) => changeDataset(e.target.value)} title="Demo veri seti">
            {datasets.map((d) => <option key={d.key} value={d.key}>{d.name}</option>)}
          </select>
          <select value={aiProvider} onChange={(e) => setAIProvider(e.target.value as AIProvider)} title="AI sağlayıcı">
            <option value="auto">AI: Otomatik</option>
            <option value="ollama">AI: Ollama</option>
            <option value="gemini">AI: Gemini</option>
            <option value="openai">AI: OpenAI</option>
            <option value="local">AI: Yerel CFO</option>
          </select>
          <button className="ghost" onClick={() => loadDataset()}><RefreshCw /> Yenile</button>
        </div>
      </header>

      <nav className="tabs">
        {[
          ['overview', 'Özet'],
          ['products', 'Ürünler'],
          ['receivables', 'Tahsilat'],
          ['ai', 'AI CFO'],
          ['upload', 'Veri yükle'],
        ].map(([key, label]) => (
          <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key as Tab)}>{label}<ChevronRight /></button>
        ))}
      </nav>

      {error && <div className="errorBox">{error}</div>}
      {result && tab === 'overview' && <Overview result={result} />}
      {result && tab === 'products' && <ProductsView result={result} datasetKey={datasetKey} />}
      {result && tab === 'receivables' && <ReceivablesView receivables={result.receivable_priorities} />}
      {result && tab === 'ai' && <AIChat result={result} datasetKey={datasetKey} aiProvider={aiProvider} setAIProvider={setAIProvider} />}
      {tab === 'upload' && <UploadView onUploaded={(r) => { setResult(r); setTab('overview') }} />}
    </main>
  )
}
