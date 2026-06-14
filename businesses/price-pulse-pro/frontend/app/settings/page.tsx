import { getApiBaseUrl } from "@/lib/api";

export default function SettingsPage() {
  const apiBaseUrl = getApiBaseUrl();

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="mt-2 text-muted">
          Configure dashboard preferences and integration endpoints.
        </p>
      </header>

      <section className="rounded-lg border border-border bg-surface-raised p-6">
        <h2 className="text-lg font-medium text-white">Environment</h2>
        <dl className="mt-4 space-y-4 text-sm">
          <div>
            <dt className="font-medium text-white">API base URL</dt>
            <dd className="mt-1 font-mono text-muted">{apiBaseUrl}</dd>
            <p className="mt-1 text-xs text-muted">
              Set via <code className="rounded bg-surface-overlay px-1 py-0.5">NEXT_PUBLIC_API_BASE_URL</code> in your environment.
            </p>
          </div>
        </dl>
      </section>
    </div>
  );
}
