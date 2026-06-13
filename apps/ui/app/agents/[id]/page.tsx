"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { Card, PageHeader, StatusBadge } from "@/components/ui";
import { money } from "@/lib/utils";

export default function AgentInspector() {
  const params = useParams<{ id: string }>();
  const { data: agent } = useFetch(() => api.agent(params.id), [params.id]);

  if (!agent) return <p className="text-sm text-slate-400">Loading agent…</p>;

  return (
    <div>
      <Link href="/agents" className="text-xs text-slate-500 hover:text-slate-300">
        ← Agents
      </Link>
      <PageHeader title={`🤖 ${agent.name}`} subtitle={`${agent.role} · ${agent.scope}`} />
      <div className="mb-6">
        <StatusBadge status={agent.status} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-lg font-semibold text-white">Overview</h2>
          <dl className="space-y-2 text-sm">
            <Row label="Scope" value={agent.scope} />
            <Row label="Status" value={agent.status} />
            <Row label="Total cost" value={money(agent.cost_total)} />
            <Row label="Last active" value={agent.last_active_at ?? "—"} />
          </dl>
        </Card>

        <Card>
          <h2 className="mb-3 text-lg font-semibold text-white">Skills</h2>
          {agent.skills?.length ? (
            <ul className="list-disc pl-5 text-sm text-slate-300">
              {agent.skills.map((s, i) => (
                <li key={i}>{String(s)}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No skills learned yet.</p>
          )}
        </Card>

        <Card>
          <h2 className="mb-3 text-lg font-semibold text-white">Tools & MCP servers</h2>
          {agent.tools?.length ? (
            <ul className="list-disc pl-5 text-sm text-slate-300">
              {agent.tools.map((t, i) => (
                <li key={i}>{String(t)}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No tools configured.</p>
          )}
        </Card>

        <Card>
          <h2 className="mb-3 text-lg font-semibold text-white">Permissions</h2>
          <pre className="overflow-auto rounded-lg bg-black/30 p-3 text-xs text-slate-300">
            {JSON.stringify(agent.permissions ?? {}, null, 2)}
          </pre>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-slick-border/60 pb-2">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-slate-200">{value}</dd>
    </div>
  );
}
