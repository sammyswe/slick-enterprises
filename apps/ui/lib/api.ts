// Client-side API helpers for the gateway.
// Browser fetches use NEXT_PUBLIC_GATEWAY_URL (LAN-only in v1).

export const GATEWAY_URL =
  process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8000";

export type Business = {
  id: string;
  slug: string;
  name: string;
  description: string;
  status: string;
  created_at: string;
};

export type Agent = {
  id: string;
  name: string;
  role: string;
  scope: string;
  status: string;
  business_id: string | null;
  skills: string[];
  tools: string[];
  permissions: Record<string, unknown>;
  cost_total: number;
  last_active_at: string | null;
};

export type Task = {
  id: string;
  business_id: string | null;
  title: string;
  description: string;
  status: string;
  assigned_agent_id: string | null;
  clarifying_questions: string[];
  result_summary: string;
  created_at: string;
};

export type CursorAccountUsage = {
  configured: boolean;
  sync_status: string;
  sync_error: string;
  last_synced_at: string | null;
  plan_name: string;
  billing_cycle_start: string | null;
  billing_cycle_end: string | null;
  total_spend_cents: number;
  included_spend_cents: number;
  limit_cents: number;
  remaining_cents: number;
  total_percent_used: number;
  auto_percent_used: number;
  api_percent_used: number;
  on_demand_spend_cents: number;
  on_demand_limit_cents: number;
  display_message: string;
};

export type HqFactoryRuns = {
  total_runs: number;
  total_duration_ms: number;
  by_purpose: Record<string, number>;
  by_model_runs: Record<string, number>;
  by_business_runs: Record<string, number>;
};

export type CostSummary = {
  billing_model: string;
  budget_usd: number;
  spent_usd: number;
  remaining_usd: number;
  hard_cap_usd: number;
  alert_step_usd: number;
  paused: boolean;
  by_business: Record<string, number>;
  by_model: Record<string, number>;
  cursor_account_usage: CursorAccountUsage;
  hq_factory_runs: HqFactoryRuns;
  total_runs: number;
  total_duration_ms: number;
  by_purpose: Record<string, number>;
  by_model_runs: Record<string, number>;
  by_business_runs: Record<string, number>;
  cursor_dashboard_url: string;
};

export type CostEvent = {
  id: string;
  business_id: string | null;
  agent_id: string | null;
  task_id: string | null;
  provider: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  estimated_cost: number;
  purpose: string;
  meta: Record<string, unknown>;
  created_at: string;
};

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${GATEWAY_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  businesses: () => getJSON<Business[]>("/businesses"),
  business: (slug: string) => getJSON<Business>(`/businesses/${slug}`),
  agents: (businessId?: string) =>
    getJSON<Agent[]>(`/agents${businessId ? `?business_id=${businessId}` : ""}`),
  agent: (id: string) => getJSON<Agent>(`/agents/${id}`),
  tasks: (businessId?: string) =>
    getJSON<Task[]>(`/tasks${businessId ? `?business_id=${businessId}` : ""}`),
  costSummary: () => getJSON<CostSummary>("/costs/summary"),
  costEvents: () => getJSON<CostEvent[]>("/costs"),
  syncCursorUsage: () =>
    fetch(`${GATEWAY_URL}/costs/sync-cursor`, { method: "POST", cache: "no-store" }).then(
      (res) => {
        if (!res.ok) throw new Error(`/costs/sync-cursor -> ${res.status}`);
        return res.json() as Promise<CostSummary>;
      }
    ),
};
