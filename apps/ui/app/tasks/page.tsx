"use client";

import { api } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { Card, EmptyState, PageHeader, StatusBadge } from "@/components/ui";

export default function TasksPage() {
  const { data, loading } = useFetch(() => api.tasks());

  return (
    <div>
      <PageHeader title="Tasks" subtitle="Units of work flowing through the autonomous loop" />
      {loading && <p className="text-sm text-slate-400">Loading…</p>}
      {!loading && !data?.length && <EmptyState message="No tasks yet." />}
      <div className="space-y-3">
        {data?.map((t) => (
          <Card key={t.id}>
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-white">{t.title}</div>
                <div className="text-xs text-slate-500">{t.description}</div>
              </div>
              <StatusBadge status={t.status} />
            </div>
            {t.result_summary && (
              <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap rounded-lg bg-black/30 p-3 text-xs text-slate-400">
                {t.result_summary}
              </pre>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
