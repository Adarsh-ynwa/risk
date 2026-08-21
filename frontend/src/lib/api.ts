const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

export interface Stats {
  transactions_analyzed: number;
  high_risk_transactions: number;
  critical_transactions: number;
  amount_at_risk: number;
  fraud_detection_rate: number;
  total_transactions: number;
  fraud_count: number;
}

export interface TriggeredRule {
  rule_id: string;
  name: string;
  severity: string;
  points: number;
  explanation: string;
}

export interface TransactionSummary {
  transaction_id: string;
  customer_id: string;
  transaction_amount: number;
  payment_method: string;
  city: string;
  country: string;
  merchant_category: string;
  risk_score: number | null;
  risk_level: string | null;
  status: string;
  transaction_date: string;
  is_fraud: boolean;
}

export interface TransactionDetail extends TransactionSummary {
  transaction_time: string;
  hour_of_day: number;
  is_weekend: boolean;
  is_night_transaction: boolean;
  merchant_category: string;
  device_type: string;
  customer_age: number;
  credit_score: number;
  account_age_years: number;
  account_balance: number;
  num_prev_transactions: number;
  transaction_freq_monthly: number;
  distance_from_home_km: number;
  time_since_last_txn_hrs: number;
  is_international: boolean;
  failed_attempts: number;
  pin_changed_recently: boolean;
  action: string | null;
  fraud_probability: number | null;
  ml_score: number | null;
  rule_score: number | null;
  triggered_rules: TriggeredRule[];
}

export interface ToolCallRecord {
  tool: string;
  reason: string;
  result_summary: string;
}

export interface InvestigationReport {
  risk_level: string;
  confidence: number;
  summary: string;
  primary_risk_factors: string[];
  investigation_findings: string[];
  recommended_action: string;
  recommended_action_reason: string;
  requires_human_review: boolean;
  tool_calls?: ToolCallRecord[];
}

export interface RiskAnalyzeResponse {
  transaction_id: string;
  fraud_probability: number;
  ml_score: number;
  rule_score: number;
  risk_score: number;
  risk_level: string;
  triggered_rules: TriggeredRule[];
  automated_action?: string | null;
  requires_human_approval?: boolean;
}

export interface TransactionCreateRequest {
  customer_id: string;
  transaction_amount: number;
  country: string;
  city: string;
  merchant_category: string;
  payment_method: string;
  device_type: string;
  account_balance: number;
  customer_age: number;
  credit_score: number;
  account_age_years: number;
  num_prev_transactions: number;
  transaction_freq_monthly: number;
  distance_from_home_km: number;
  time_since_last_txn_hrs: number;
  is_international: boolean;
  failed_attempts: number;
  pin_changed_recently: boolean;
}

export interface ActionResponse {
  transaction_id: string;
  action: string;
  previous_status: string;
  new_status: string;
  timestamp: string;
}

export interface TransactionFilters {
  payment_methods: string[];
  merchant_categories: string[];
  statuses: string[];
}

export interface FraudProbBucket {
  bucket: string;
  count: number;
}

export interface AnalyticsData {
  stats: Stats;
  risk_summary: RiskSummary;
  international_fraud_count: number;
  night_transaction_fraud_count: number;
  failed_attempt_fraud_count: number;
  fraud_probability_distribution: FraudProbBucket[];
}

export interface PaginatedTransactions {
  items: TransactionSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RiskSummary {
  risk_distribution: Record<string, number>;
  fraud_vs_legitimate: Record<string, number>;
  risk_trend: { date: string; avg_risk_score: number; count: number }[];
  fraud_by_category: { category: string; count: number }[];
  amount_at_risk_by_level: Record<string, number>;
}

function buildQuery(params: Record<string, string | number | boolean | undefined>) {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  return new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
}

export const api = {
  health: () => fetchApi<{ status: string; model_loaded: boolean; database_connected: boolean; groq_configured: boolean }>("/health"),
  stats: () => fetchApi<Stats>("/stats"),
  transactionFilters: () => fetchApi<TransactionFilters>("/transactions/filters"),
  transactions: (params: Record<string, string | number | boolean | undefined>) => {
    return fetchApi<PaginatedTransactions>(`/transactions?${buildQuery(params)}`);
  },
  transaction: (id: string) => fetchApi<TransactionDetail>(`/transactions/${id}`),
  createTransaction: (transaction: TransactionCreateRequest) =>
    fetchApi<RiskAnalyzeResponse>("/transactions", {
      method: "POST",
      body: JSON.stringify(transaction),
    }),
  highestRisk: () => fetchApi<{ transaction_id: string }>("/transactions/highest-risk"),
  analyzeRisk: (transaction_id: string) =>
    fetchApi<RiskAnalyzeResponse>("/risk/analyze", {
      method: "POST",
      body: JSON.stringify({ transaction_id }),
    }),
  investigate: (transaction_id: string) =>
    fetchApi<{ transaction_id: string; investigation: InvestigationReport; is_fallback: boolean; final_status?: string; action_applied?: string; requires_human_approval?: boolean }>(
      `/investigations/${transaction_id}`,
      { method: "POST" }
    ),
  getInvestigation: (transaction_id: string) =>
    fetchApi<{ transaction_id: string; investigation: InvestigationReport; is_fallback: boolean }>(
      `/investigations/${transaction_id}`
    ),
  action: (transaction_id: string, action: string) =>
    fetchApi<ActionResponse>(`/actions/${transaction_id}`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),
  riskSummary: () => fetchApi<RiskSummary>("/risk/summary"),
  analytics: () => fetchApi<AnalyticsData>("/analytics"),
  modelMetrics: () => fetchApi<Record<string, unknown>>("/model/metrics"),
};
