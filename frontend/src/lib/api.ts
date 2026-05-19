import type { AIProvider, AIStatus, AnalysisResult, ChatResponse, DatasetInfo, PriceScenarioResult, ScenarioSuite } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function getDatasets(): Promise<DatasetInfo[]> {
  const data = await request<{ datasets: DatasetInfo[] }>('/api/datasets')
  return data.datasets
}

export async function getDemoAnalysis(datasetKey: string = 'default'): Promise<AnalysisResult> {
  return datasetKey === 'default'
    ? request<AnalysisResult>('/api/demo')
    : request<AnalysisResult>(`/api/demo/${encodeURIComponent(datasetKey)}`)
}

export async function getAIStatus(): Promise<AIStatus> {
  return request('/api/ai/status')
}

export async function uploadAnalysis(form: FormData): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json() as Promise<AnalysisResult>
}

export async function runPriceScenario(sku: string, newPrice: number, datasetKey: string = 'default'): Promise<PriceScenarioResult> {
  return request<PriceScenarioResult>('/api/what-if/price', {
    method: 'POST',
    body: JSON.stringify({ sku, new_price: newPrice, use_demo: true, dataset_key: datasetKey }),
  })
}

export async function runCrisisScenario(datasetKey: string = 'default'): Promise<ScenarioSuite> {
  return request<ScenarioSuite>('/api/what-if/crisis', {
    method: 'POST',
    body: JSON.stringify({ use_demo: true, dataset_key: datasetKey }),
  })
}

export async function askChat(question: string, datasetKey: string = 'default', provider: AIProvider = 'auto'): Promise<ChatResponse> {
  return request<ChatResponse>('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ question, use_demo: true, dataset_key: datasetKey, llm_provider: provider }),
  })
}

export async function createCollectionMessage(customerName: string, amount: number, delayDays: number, tone: string = 'firm'): Promise<string> {
  const data = await request<{ message: string }>('/api/collection-message', {
    method: 'POST',
    body: JSON.stringify({ customer_name: customerName, amount, delay_days: delayDays, tone }),
  })
  return data.message
}

export function reportUrl(): string {
  return `${API_BASE}/api/report/demo.md`
}

export function templateReadmeUrl(): string {
  return `${API_BASE}/api/templates/readme`
}
