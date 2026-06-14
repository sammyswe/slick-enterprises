export default function AlertsPage() {
  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-white">Alerts</h1>
        <p className="mt-2 text-muted">
          Configure alert rules and review the live feed of price changes.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-border bg-surface-raised p-6">
          <h2 className="text-lg font-medium text-white">Alert configuration</h2>
          <p className="mt-2 text-sm text-muted">
            Set thresholds and notification channels for price drop alerts.
          </p>
        </section>

        <section className="rounded-lg border border-border bg-surface-raised p-6">
          <h2 className="text-lg font-medium text-white">Alert feed</h2>
          <p className="mt-2 text-sm text-muted">
            Recent price-change notifications will stream here.
          </p>
        </section>
      </div>
    </div>
  );
}
