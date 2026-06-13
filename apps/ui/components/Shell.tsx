"use client";

import { usePathname } from "next/navigation";
import { Nav } from "@/components/Nav";

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  // The login screen is full-bleed (no sidebar).
  if (pathname === "/login") {
    return <>{children}</>;
  }
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-slick-border bg-slick-panel/60 p-4 md:flex">
        <div className="mb-6 px-2">
          <div className="text-lg font-bold text-white">🤠 Slick HQ</div>
          <div className="text-xs text-slate-500">Sheriff S command deck</div>
        </div>
        <Nav />
        <div className="mt-auto px-2 text-xs text-slate-600">v1 scaffold · mock-safe</div>
      </aside>
      <main className="flex-1 p-6 md:p-8">{children}</main>
    </div>
  );
}
