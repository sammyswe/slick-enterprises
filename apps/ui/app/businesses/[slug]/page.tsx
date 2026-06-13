"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { Card, EmptyState, PageHeader, StatusBadge } from "@/components/ui";

export default function BusinessRoom() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const business = useFetch(() => api.business(slug), [slug]);
  const bId = business.data?.id;
  const agents = useFetch(() => (bId ? api.agents(bId) : Promise.resolve([])), [bId]);
  const tasks = useFetch(() => (bId ? api.tasks(bId) : Promise.resolve([])), [bId]);

  if (!business.data) {
    return <p className="text-sm text-slate-400">Loading compartment…</p>;
  }

  return (
    <div>
      <Link href="/businesses" className="text-xs text-slate-500 hover:text-slate-300">
        ← Businesses
      </Link>
      <PageHeader title={`🚪 ${business.data.name}`} subtitle={business.data.description} />
      <div className="mb-6 flex items-center gap-3">
        <StatusBadge status={business.data.status} />
        <span className="font-mono text-xs text-slate-500">{business.data.slug}</span>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-white">Agents</h2>
          {agents.data?.length ? (
            <div className="space-y-2">
              {agents.data.map((a) => (
                <Link
                  key={a.id}
                  href={`/agents/${a.id}`}
                  className="flex items-center justify-between rounded-lg border border-slick-border p-3 hover:bg-slick-border/40"
                >
                  <div>
                    <div className="text-sm font-medium text-white">{a.name}</div>
                    <div className="text-xs text-slate-500">{a.role}</div>
                  </div>
                  <StatusBadge status={a.status} />
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState message="No agents staffed yet." />
          )}
        </Card>

        <Card>
          <h2 className="mb-4 text-lg font-semibold text-white">Tasks</h2>
          {tasks.data?.length ? (
            <div className="space-y-2">
              {tasks.data.map((t) => (
                <div key={t.id} className="rounded-lg border border-slick-border p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-200">{t.title}</span>
                    <StatusBadge status={t.status} />
                  </div>
                  {t.clarifying_questions?.length > 0 && (
                    <ul className="mt-2 list-disc pl-5 text-xs text-slate-500">
                      {t.clarifying_questions.slice(0, 4).map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState message="No tasks yet." />
          )}
        </Card>
      </div>
    </div>
  );
}
