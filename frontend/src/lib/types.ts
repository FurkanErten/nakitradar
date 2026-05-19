export interface DatasetInfo {
  key: string
  name: string
  description: string
}

export type AIProvider = 'auto' | 'ollama' | 'gemini' | 'openai' | 'local'

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export interface BusinessProfile {
  business_name: string
  sector: string
  monthly_revenue_target: number
  owner_email?: string | null
}

export interface CashFlowPoint {
  date: string
  opening_cash: number
  expected_inflow: number
  expected_outflow: number
  closing_cash: number
  notes: string[]
}

export interface ProductProfitability {
  sku: string
  name: string
  category: string
  units_sold: number
  revenue: number
  total_cost: number
  net_profit: number
  margin: number
  return_rate: number
  avg_profit_per_unit: number
  current_price: number
  break_even_price: number
  recommended_price: number
  max_safe_discount_percent: number
  stock_value: number
  days_of_inventory: number | null
  health_score: number
  status: 'grow' | 'watch' | 'liquidate' | 'stop'
  reasons: string[]
  commission_rate: number
  ad_rate: number
  payment_fee_rate: number
  average_shipping_cost: number
  average_return_cost: number
  safe_campaign_discount_percent: number
  next_step: string
}

export interface ReceivablePriority {
  id: string
  customer_name: string
  amount: number
  due_date: string
  delay_days: number
  probability: number
  priority_score: number
  level: RiskLevel
  impact: string
  suggested_message: string
  collection_strategy: 'soft' | 'balanced' | 'firm' | 'legal_warning'
}

export interface RiskBreakdown {
  payment_pressure: number
  receivable_risk: number
  low_profit_product_risk: number
  stock_locked_risk: number
  revenue_uncertainty: number
  total_score: number
  level: RiskLevel
}

export interface FinancialSnapshot {
  gross_sales: number
  paper_profit: number
  real_net_profit: number
  marketplace_costs: number
  shipping_and_packaging_costs: number
  return_costs: number
  ad_spend: number
  overdue_receivables: number
  locked_inventory_cash: number
  cash_conversion_gap: number
  loss_making_products_count: number
  dangerous_campaign_products_count: number
}

export interface CrisisAlert {
  title: string
  description: string
  critical_day: string | null
  minimum_cash: number
  cash_gap: number
  root_causes: string[]
  survival_plan: string[]
}

export interface ScenarioCase {
  name: string
  description: string
  day_14_cash: number
  minimum_cash: number
  cash_gap: number
  risk_score: number
  interpretation: string
}

export interface ScenarioSuite {
  base_case: ScenarioCase
  top_receivable_collected: ScenarioCase | null
  stock_purchase_frozen: ScenarioCase | null
  price_fix_applied: ScenarioCase | null
  combined_rescue: ScenarioCase | null
}

export interface DailyCFOBrief {
  morning_summary: string
  top_priorities: string[]
  forbidden_actions: string[]
  safe_actions: string[]
}

export interface DataQualityIssue {
  severity: 'info' | 'warning' | 'critical'
  entity: string
  message: string
  recommendation: string
}

export interface IntegrationConnector {
  name: string
  category: 'marketplace' | 'banking' | 'accounting' | 'shipping' | 'ads' | 'communication'
  status: 'ready_for_csv' | 'api_planned' | 'manual'
  data_needed: string[]
  value: string
}

export interface ActionItem {
  title: string
  detail: string
  impact: string
  priority: 'critical' | 'high' | 'medium' | 'low'
  category: 'cashflow' | 'receivable' | 'pricing' | 'inventory' | 'marketplace' | 'general' | 'data' | 'security'
}

export interface ExecutiveSummary {
  headline: string
  narrative: string
  critical_day: string | null
  minimum_cash: number
  cash_gap: number
  top_risks: string[]
  today_actions: string[]
}

export interface InventoryRisk {
  sku: string
  name: string
  stock_count: number
  stock_value: number
  days_of_inventory: number | null
  risk_level: RiskLevel
  action: string
  locked_cash_ratio: number
}

export interface AnalysisResult {
  generated_at: string
  analysis_date: string
  profile: BusinessProfile
  summary: ExecutiveSummary
  financial_snapshot: FinancialSnapshot
  crisis_alert: CrisisAlert
  risk: RiskBreakdown
  cashflow: CashFlowPoint[]
  product_profitability: ProductProfitability[]
  receivable_priorities: ReceivablePriority[]
  inventory_risks: InventoryRisk[]
  scenario_suite: ScenarioSuite
  daily_brief: DailyCFOBrief
  data_quality_issues: DataQualityIssue[]
  integration_roadmap: IntegrationConnector[]
  actions: ActionItem[]
}

export interface PriceScenarioResult {
  sku: string
  old_price: number
  new_price: number
  old_profit_per_unit: number
  new_profit_per_unit: number
  old_margin: number
  new_margin: number
  estimated_sales_change_percent: number
  projected_monthly_profit_delta: number
  break_even_price: number
  recommended_price: number
  old_safe_discount_percent: number
  new_safe_discount_percent: number
  interpretation: string
}


export interface ChatResponse {
  answer: string
  provider: 'local' | 'openai' | 'ollama' | 'gemini' | 'error_fallback'
  model?: string | null
  used_tools: string[]
  evidence: string[]
  suggested_questions: string[]
}


export interface AIProviderOption {
  key: AIProvider
  label: string
  description: string
  configured: boolean
  reachable?: boolean | null
}

export interface AIStatus {
  enabled: boolean
  provider: string
  active_order?: string[]
  model?: string | null
  message: string
  ollama_reachable?: boolean | null
  gemini_configured?: boolean
  openai_configured?: boolean
  provider_options?: AIProviderOption[]
}
