"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { Card, PageHeader, Stat, StatusBadge } from "@/components/ui";
import { money, formatDuration } from "@/lib/utils";

function centsToDollars(cents: number): string {
  return money(cents / 100);
}

export default function DashboardPage() {
  const businesses = useFetch(() => api.businesses());
  const agents = useFetch(() => api.agents());
  const tasks = useFetch(() => api.tasks());
  const cost = useFetch(() => api.costSummary());

  const activeAgents = agents.data?.filter((a) => a.status === "active").length ?? 0;
  const sleeping = agents.data?.filter((a) => a.status === "sleeping").length ?? 0;
  const inProgress = tasks.data?.filter((t) => t.status === "in_progress").length ?? 0;

  return (
    <div>
      <PageHeader
        title="🤠 Sheriff S Command Deck"
        subtitle="Overview of your AI business factory"
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Businesses" value={businesses.data?.length ?? "—"} />
        <Stat label="Agents" value={agents.data?.length ?? "—"} hint={`${activeAgents} active · ${sleeping} asleep ($0)`} />
        <Stat label="Tasks in progress" value={inProgress} />
        <Stat
          label={cost.data?.billing_model === "cursor" ? "Cursor spending" : "Budget used"}
          value={
            cost.data?.billing_model === "cursor"
              ? cost.data.cursor_account_usage?.configured
                ? `${(cost.data.cursor_account_usage.total_percent_used ?? 0).toFixed(1)}%`
                : (cost.data.hq_factory_runs?.total_runs ?? cost.data.total_runs ?? "—")
              : cost.data
                ? money(cost.data.spent_usd)
                : "—"
          }
          hint={
            cost.data?.billing_model === "cursor"
              ? cost.data.cursor_account_usage?.configured
                ? `${centsToDollars(cost.data.cursor_account_usage.included_spend_cents)} included · dashboard sync`
                : `${formatDuration(cost.data.total_duration_ms)} HQ runs · configure token to sync`
              : cost.data
                ? `of ${money(cost.data.budget_usd)}${cost.data.paused ? " · PAUSED" : ""}`
                : undefined
          }
        />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-white">Businesses</h2>
          <div className="space-y-2">
            {businesses.data?.length ? (
              businesses.data.map((b) => (
                <Link
                  key={b.id}
                  href={`/businesses/${b.slug}`}
                  className="flex items-center justify-between rounded-lg border border-slick-border p-3 hover:bg-slick-border/40"
                >
                  <div>
                    <div className="font-medium text-white">{b.name}</div>
                    <div className="text-xs text-slate-500">{b.slug}</div>
                  </div>
                  <StatusBadge status={b.status} />
                </Link>
              ))
            ) : (
              <p className="text-sm text-slate-400">No businesses yet. Send an idea to Sheriff S.</p>
            )}
          </div>
        </Card>

        <Card>
          <h2 className="mb-4 text-lg font-semibold text-white">Recent tasks</h2>
          <div className="space-y-2">
            {tasks.data?.length ? (
              tasks.data.slice(0, 6).map((t) => (
                <div
                  key={t.id}
                  className="flex items-center justify-between rounded-lg border border-slick-border p-3"
                >
                  <span className="truncate pr-3 text-sm text-slate-200">{t.title}</span>
                  <StatusBadge status={t.status} />
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-400">No tasks yet.</p>
            )}
          </div>
        </Card>
      </div>

      {(businesses.error || agents.error || tasks.error || cost.error) && (
        <p className="mt-6 text-sm text-rose-400">
          Could not reach the gateway at{" "}
          {process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8000"}. Try{" "}
          <code>make up</code> then <code>make migrate</code>.
        </p>
      )}
    </div>
  );
}
