"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { Card, EmptyState, PageHeader, StatusBadge } from "@/components/ui";

export default function BusinessesPage() {
  const { data, loading } = useFetch(() => api.businesses());

  return (
    <div>
      <PageHeader title="Businesses" subtitle="One isolated compartment per business" />
      {loading && <p className="text-sm text-slate-400">Loading…</p>}
      {!loading && !data?.length && <EmptyState message="No businesses yet. Send an idea to Sheriff S in Discord." />}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {data?.map((b) => (
          <Link key={b.id} href={`/businesses/${b.slug}`}>
            <Card className="h-full transition-colors hover:border-slick-accent/60">
              <div className="flex items-start justify-between">
                <h2 className="text-lg font-semibold text-white">{b.name}</h2>
                <StatusBadge status={b.status} />
              </div>
              <p className="mt-1 font-mono text-xs text-slate-500">{b.slug}</p>
              <p className="mt-3 text-sm text-slate-400 line-clamp-3">{b.description || "No description."}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
