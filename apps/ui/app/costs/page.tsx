"use client";

import { useCallback, useState } from "react";
import { api, type CostSummary } from "@/lib/api";
import { useFetch } from "@/lib/useFetch";
import { Card, EmptyState, PageHeader, Stat } from "@/components/ui";
import { formatDuration, money } from "@/lib/utils";

function centsToDollars(cents: number): string {
  return money(cents / 100);
}

export default function CostsPage() {
  const [syncTick, setSyncTick] = useState(0);
  const summary = useFetch(() => api.costSummary(), [syncTick]);
  const events = useFetch(() => api.costEvents(), [syncTick]);

  const handleSync = useCallback(async () => {
    await api.syncCursorUsage();
    setSyncTick((n) => n + 1);
  }, []);

  const s = summary.data;
  const isCursor = s?.billing_model === "cursor";
  const isMock = s?.billing_model === "mock";
  const account = s?.cursor_account_usage;
  const factory = s?.hq_factory_runs;

  return (
    <div>
      <PageHeader
        title="Costs"
        subtitle={
          isCursor
            ? "Cursor account billing (dashboard sync) plus HQ factory run attribution."
            : isMock
              ? "Mock mode — zero-cost deterministic responses."
              : "Per-token spend via the Anthropic API."
        }
      />

      {isCursor && (
        <>
          <CursorAccountCard
            account={account}
            dashboardUrl={s?.cursor_dashboard_url}
            onSync={handleSync}
          />
          <Card className="mb-6 border-slate-600/40">
            <h2 className="mb-3 text-lg font-semibold text-white">HQ factory attribution</h2>
            <p className="mb-4 text-sm text-slate-400">
              Composer runs initiated by Slick HQ (Sheriff S, builds, evaluations). This is not your
              full Cursor account usage — IDE chat and other sessions are only in the account card
              above.
            </p>
            <CursorFactorySummary summary={s} factory={factory} />
          </Card>
        </>
      )}

      {isCursor ? null : isMock ? (
        <DollarUsageSummary summary={s} />
      ) : (
        <DollarUsageSummary summary={s} />
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-lg font-semibold text-white">
            {isCursor ? "HQ runs by purpose" : "By business"}
          </h2>
          {isCursor ? (
            <RunBreakdown data={factory?.by_purpose ?? s?.by_purpose} />
          ) : (
            <DollarBreakdown data={s?.by_business} />
          )}
        </Card>
        <Card>
          <h2 className="mb-3 text-lg font-semibold text-white">
            {isCursor ? "HQ runs by model" : "By model"}
          </h2>
          {isCursor ? (
            <RunBreakdown data={factory?.by_model_runs ?? s?.by_model_runs} />
          ) : (
            <DollarBreakdown data={s?.by_model} />
          )}
        </Card>
      </div>

      {isCursor && Object.keys(factory?.by_business_runs ?? s?.by_business_runs ?? {}).length > 0 && (
        <Card className="mt-6">
          <h2 className="mb-3 text-lg font-semibold text-white">HQ runs by business</h2>
          <RunBreakdown data={factory?.by_business_runs ?? s?.by_business_runs} />
        </Card>
      )}

      <Card className="mt-6">
        <h2 className="mb-3 text-lg font-semibold text-white">
          {isCursor ? "Recent HQ Composer runs" : "Recent cost events"}
        </h2>
        {events.data?.length ? (
          <div className="overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="py-2">When</th>
                  <th>Purpose</th>
                  <th>Model</th>
                  {isCursor ? (
                    <>
                      <th>Mode</th>
                      <th>Duration</th>
                      <th>Status</th>
                    </>
                  ) : (
                    <>
                      <th>Tokens (in/out)</th>
                      <th className="text-right">Cost</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {events.data.map((e) => {
                  const meta = e.meta ?? {};
                  const duration = Number(meta.duration_ms ?? 0);
                  const status = String(meta.status ?? "—");
                  const mode = String(meta.mode ?? "—");
                  return (
                    <tr key={e.id} className="border-t border-slick-border/60">
                      <td className="py-2 text-xs text-slate-500">
                        {new Date(e.created_at).toLocaleString()}
                      </td>
                      <td className="text-slate-300">{e.purpose || "—"}</td>
                      <td className="font-mono text-xs text-slate-400">{e.model}</td>
                      {isCursor ? (
                        <>
                          <td className="text-slate-400">{mode}</td>
                          <td className="text-slate-400">{formatDuration(duration)}</td>
                          <td className="text-slate-400">{status || "—"}</td>
                        </>
                      ) : (
                        <>
                          <td className="text-slate-400">
                            {e.tokens_in}/{e.tokens_out}
                          </td>
                          <td className="text-right">{money(e.estimated_cost)}</td>
                        </>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            message={
              isCursor
                ? "No HQ Composer runs logged yet. Runs appear after Sheriff S or the build engine calls the Cursor SDK."
                : "No cost events yet."
            }
          />
        )}
      </Card>
    </div>
  );
}

function CursorAccountCard({
  account,
  dashboardUrl,
  onSync,
}: {
  account: CostSummary["cursor_account_usage"] | undefined;
  dashboardUrl?: string;
  onSync: () => Promise<void>;
}) {
  const configured = account?.configured && account.sync_status === "ok";
  const pct = account?.total_percent_used ?? 0;
  const autoPct = account?.auto_percent_used ?? 0;
  const apiPct = account?.api_percent_used ?? 0;

  return (
    <Card className="mb-6 border-sky-500/30 bg-sky-500/5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Cursor account (billing cycle)</h2>
          <p className="text-sm text-slate-400">
            Synced from the same API as{" "}
            <a
              href={dashboardUrl ?? "https://cursor.com/dashboard?tab=usage"}
              target="_blank"
              rel="noreferrer"
              className="text-sky-400 underline hover:text-sky-300"
            >
              cursor.com/dashboard
            </a>
            . <strong className="text-slate-300">Spending %</strong> controls your quota; Usage $
            is informational.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void onSync()}
          className="rounded-lg border border-sky-500/40 bg-sky-500/10 px-3 py-1.5 text-sm text-sky-300 hover:bg-sky-500/20"
        >
          Sync now
        </button>
      </div>

      {!account?.configured ? (
        <p className="text-sm text-amber-200/90">
          Not configured. Set <code className="text-amber-100">CURSOR_ACCESS_TOKEN</code> or{" "}
          <code className="text-amber-100">CURSOR_WORKOS_SESSION_TOKEN</code> in{" "}
          <code className="text-amber-100">.env</code> and restart cost-controller. See{" "}
          <code className="text-amber-100">docs/08-cost-control.md</code>.
          {account?.sync_error ? (
            <span className="mt-2 block text-rose-300">{account.sync_error}</span>
          ) : null}
        </p>
      ) : account.sync_status === "error" ? (
        <p className="text-sm text-rose-300">Sync error: {account.sync_error}</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat
              label="Included spend"
              value={centsToDollars(account.included_spend_cents)}
              hint={
                account.limit_cents
                  ? `of ${centsToDollars(account.limit_cents)} limit`
                  : account.plan_name || undefined
              }
            />
            <Stat
              label="Remaining"
              value={
                account.remaining_cents ? centsToDollars(account.remaining_cents) : "—"
              }
            />
            <Stat
              label="Spending %"
              value={pct ? `${pct.toFixed(1)}%` : "—"}
              hint="authoritative quota metric"
            />
            <Stat
              label="Plan"
              value={account.plan_name || "Cursor"}
              hint={
                account.last_synced_at
                  ? `synced ${new Date(account.last_synced_at).toLocaleString()}`
                  : undefined
              }
            />
          </div>
          {configured && (autoPct > 0 || apiPct > 0) && (
            <div className="mt-4 grid grid-cols-2 gap-4 text-sm text-slate-400">
              <span>Auto: {autoPct.toFixed(1)}%</span>
              <span>API: {apiPct.toFixed(1)}%</span>
            </div>
          )}
          {account.display_message ? (
            <p className="mt-3 text-sm text-slate-300">{account.display_message}</p>
          ) : null}
          <div className="mt-4">
            <div className="mb-2 flex justify-between text-sm text-slate-400">
              <span>Spending % (billing cycle)</span>
              <span>{pct.toFixed(1)}%</span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-slick-border">
              <div
                className={
                  pct >= 100 ? "h-full bg-rose-500" : pct >= 80 ? "h-full bg-amber-400" : "h-full bg-emerald-500"
                }
                style={{ width: `${Math.min(100, pct)}%` }}
              />
            </div>
          </div>
        </>
      )}
    </Card>
  );
}

function CursorFactorySummary({
  summary: s,
  factory,
}: {
  summary: CostSummary | null | undefined;
  factory: CostSummary["hq_factory_runs"] | undefined;
}) {
  const runs = factory?.total_runs ?? s?.total_runs ?? 0;
  const duration = factory?.total_duration_ms ?? s?.total_duration_ms ?? 0;
  const avgMs = runs > 0 ? Math.round(duration / runs) : 0;
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Stat label="HQ Composer runs" value={runs} hint="logged SDK calls" />
      <Stat label="Total compute" value={formatDuration(duration)} hint="sum of run durations" />
      <Stat label="Avg per run" value={avgMs ? formatDuration(avgMs) : "—"} />
      <Stat label="Provider" value="Cursor SDK" hint="factory attribution only" />
    </div>
  );
}

function DollarUsageSummary({ summary: s }: { summary: CostSummary | null | undefined }) {
  const pct = s ? Math.min(100, (s.spent_usd / s.budget_usd) * 100) : 0;
  return (
    <>
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
    </>
  );
}

function RunBreakdown({ data }: { data?: Record<string, number> }) {
  const entries = Object.entries(data ?? {}).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return <p className="text-sm text-slate-500">No runs yet.</p>;
  const max = entries[0][1];
  return (
    <ul className="space-y-2 text-sm">
      {entries.map(([k, v]) => (
        <li key={k}>
          <div className="mb-1 flex justify-between">
            <span className="text-slate-300">{k}</span>
            <span className="text-slate-400">{v} run{v === 1 ? "" : "s"}</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slick-border">
            <div className="h-full bg-sky-500/70" style={{ width: `${(v / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

function DollarBreakdown({ data }: { data?: Record<string, number> }) {
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
