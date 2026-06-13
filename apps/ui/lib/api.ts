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

export type CostSummary = {
  budget_usd: number;
  spent_usd: number;
  remaining_usd: number;
  hard_cap_usd: number;
  alert_step_usd: number;
  paused: boolean;
  by_business: Record<string, number>;
  by_model: Record<string, number>;
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
};
