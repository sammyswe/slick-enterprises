"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Building2,
  Bot,
  ListChecks,
  DollarSign,
  Rocket,
} from "lucide-react";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/businesses", label: "Businesses", icon: Building2 },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/tasks", label: "Tasks", icon: ListChecks },
  { href: "/costs", label: "Costs", icon: DollarSign },
  { href: "/spaceship", label: "Spaceship", icon: Rocket },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-1">
      {LINKS.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn("nav-link flex items-center gap-3", active && "nav-link-active")}
          >
            <Icon size={18} />
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
