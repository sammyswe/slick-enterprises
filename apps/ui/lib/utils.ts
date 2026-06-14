import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-300",
  in_progress: "bg-sky-500/15 text-sky-300",
  sleeping: "bg-slate-500/15 text-slate-300",
  blocked: "bg-rose-500/15 text-rose-300",
  done: "bg-emerald-500/15 text-emerald-300",
  pending: "bg-amber-500/15 text-amber-300",
  clarifying: "bg-amber-500/15 text-amber-300",
  awaiting_approval: "bg-amber-500/15 text-amber-300",
  proposed: "bg-amber-500/15 text-amber-300",
  approved: "bg-emerald-500/15 text-emerald-300",
  paused: "bg-rose-500/15 text-rose-300",
  archived: "bg-slate-500/15 text-slate-300",
};

export function statusColor(status: string): string {
  return STATUS_COLORS[status] ?? "bg-slate-500/15 text-slate-300";
}

export function money(n: number): string {
  return `$${n.toFixed(2)}`;
}

export function formatDuration(ms: number): string {
  if (!ms || ms < 0) return "—";
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  if (m < 60) return rem ? `${m}m ${rem}s` : `${m}m`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return rm ? `${h}h ${rm}m` : `${h}h`;
}
