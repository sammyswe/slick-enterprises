"use client";

import { api } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { Card, EmptyState, PageHeader, Stat } from "@/components/ui";
import { money } from "@/lib/utils";

export default function CostsPage() {
  const summary = useFetch(() => api.costSummary());
  const events = useFetch(() => api.costEvents());

  const s = summary.data;
  const pct = s ? Math.min(100, (s.spent_usd / s.budget_usd) * 100) : 0;

  return (
    <div>
      <PageHeader title="Costs" subtitle="Per task, agent, business, and model. Idle agents cost $0." />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Spent" value={s ? money(s.spent_usd) : "—"} />
        <Stat label="Budget" value={s ? money(s.budget_usd) : "—"} />
        <Stat label="Remaining" value={s ? money(s.remaining_usd) : "—"} />
        <Stat label="Status" value={s?.paused ? "PAUSED" : "OK"} hint={s ? `hard cap ${money(s.hard_cap_usd)}` : undefined} />
      </div>

      <Card className="mt-6">
        <div className="mb-2 flex justify-between text-sm text-slate-400">
          <span>Budget meter</span>
          <span>{pct.toFixed(1)}%</span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-slick-border">
          <div
            className={pct >= 100 ? "h-full bg-rose-500" : pct >= 80 ? "h-full bg-amber-400" : "h-full bg-emerald-500"}
            style={{ width: `${pct}%` }}
          />
        </div>
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-lg font-semibold text-white">By business</h2>
          <Breakdown data={s?.by_business} />
        </Card>
        <Card>
          <h2 className="mb-3 text-lg font-semibold text-white">By model</h2>
          <Breakdown data={s?.by_model} />
        </Card>
      </div>

      <Card className="mt-6">
        <h2 className="mb-3 text-lg font-semibold text-white">Recent cost events</h2>
        {events.data?.length ? (
          <div className="overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="py-2">Model</th>
                  <th>Purpose</th>
                  <th>Tokens (in/out)</th>
                  <th className="text-right">Cost</th>
                </tr>
              </thead>
              <tbody>
                {events.data.map((e) => (
                  <tr key={e.id} className="border-t border-slick-border/60">
                    <td className="py-2 font-mono text-xs">{e.model}</td>
                    <td className="text-slate-400">{e.purpose || "—"}</td>
                    <td className="text-slate-400">{e.tokens_in}/{e.tokens_out}</td>
                    <td className="text-right">{money(e.estimated_cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState message="No cost events yet (mock mode reports $0)." />
        )}
      </Card>
    </div>
  );
}

function Breakdown({ data }: { data?: Record<string, number> }) {
  const entries = Object.entries(data ?? {});
  if (!entries.length) return <p className="text-sm text-slate-500">No data.</p>;
  return (
    <ul className="space-y-2 text-sm">
      {entries.map(([k, v]) => (
        <li key={k} className="flex justify-between">
          <span className="text-slate-300">{k}</span>
          <span className="text-slate-400">{money(v)}</span>
        </li>
      ))}
    </ul>
  );
}
