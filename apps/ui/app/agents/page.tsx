"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { Card, EmptyState, PageHeader, StatusBadge } from "@/components/ui";
import { money } from "@/lib/utils";

export default function AgentsPage() {
  const { data, loading } = useFetch(() => api.agents());
  const globals = data?.filter((a) => a.scope === "global") ?? [];
  const business = data?.filter((a) => a.scope === "business") ?? [];

  return (
    <div>
      <PageHeader title="Agents" subtitle="Click an agent to inspect status, skills, tools, permissions, and cost" />
      {loading && <p className="text-sm text-slate-400">Loading…</p>}
      {!loading && !data?.length && <EmptyState message="No agents registered. Run `make seed`." />}

      {globals.length > 0 && (
        <section className="mb-8">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Global agents</h2>
          <AgentGrid agents={globals} />
        </section>
      )}
      {business.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Business agents</h2>
          <AgentGrid agents={business} />
        </section>
      )}
    </div>
  );
}

function AgentGrid({ agents }: { agents: { id: string; name: string; role: string; status: string; cost_total: number }[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {agents.map((a) => (
        <Link key={a.id} href={`/agents/${a.id}`}>
          <Card className="h-full transition-colors hover:border-slick-accent/60">
            <div className="flex items-start justify-between">
              <div className="text-3xl">🤖</div>
              <StatusBadge status={a.status} />
            </div>
            <div className="mt-2 font-medium text-white">{a.name}</div>
            <div className="text-xs text-slate-500">{a.role}</div>
            <div className="mt-3 text-xs text-slate-400">Cost: {money(a.cost_total)}</div>
          </Card>
        </Link>
      ))}
    </div>
  );
}
