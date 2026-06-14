import { fetchHealth, getApiBaseUrl } from "@/lib/api";

export default async function CompetitorsPage() {
  const apiBaseUrl = getApiBaseUrl();
  const health = await fetchHealth();

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-white">Competitors</h1>
        <p className="mt-2 text-muted">
          Manage competitor URLs and monitor their pricing.
        </p>
      </header>

      <section className="rounded-lg border border-border bg-surface-raised p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
          API connection
        </h2>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-medium text-white">Base URL</dt>
            <dd className="mt-1 font-mono text-muted">{apiBaseUrl}</dd>
          </div>
          <div>
            <dt className="font-medium text-white">Status</dt>
            <dd className="mt-1 capitalize text-muted">
              {health?.status ?? "unreachable"}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-white">Database</dt>
            <dd className="mt-1 capitalize text-muted">
              {health?.database ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-white">Redis</dt>
            <dd className="mt-1 capitalize text-muted">
              {health?.redis ?? "—"}
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
