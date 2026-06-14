import { Navigation } from "./Navigation";

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen">
      <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-surface-raised px-4 py-6">
        <div className="mb-8 px-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted">
            Price Pulse Pro
          </p>
          <h1 className="mt-1 text-lg font-semibold text-white">Dashboard</h1>
        </div>
        <Navigation />
      </aside>
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  );
}
