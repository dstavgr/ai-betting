"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, Lightbulb, ListOrdered, Menu } from "lucide-react";

import { LeagueSwitcher } from "@/components/LeagueSwitcher";
import { cn } from "@/lib/utils";

const tabs = [
  { href: "/", label: "Scores", icon: CalendarDays },
  { href: "/tips", label: "Tips", icon: Lightbulb },
  { href: "/table", label: "Table", icon: ListOrdered },
  { href: "/more", label: "More", icon: Menu },
];

function usePrimaryNavState() {
  const pathname = usePathname();

  return (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
}

export function BottomNav() {
  const isActive = usePrimaryNavState();

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-50 grid grid-cols-4 border-t border-border bg-card/95 shadow-sm backdrop-blur md:hidden"
      aria-label="Primary"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = isActive(tab.href);

        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`flex flex-col items-center gap-1 py-2 text-xs font-medium transition-colors ${
              active ? "text-primary" : "text-muted-foreground"
            }`}
          >
            <Icon className="h-5 w-5" aria-hidden="true" />
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function SidebarNav() {
  const isActive = usePrimaryNavState();

  return (
    <aside className="hidden w-44 shrink-0 md:block lg:w-52" aria-label="Primary">
      <nav className="sticky top-[76px] space-y-1 rounded-xl border border-border bg-card p-2 text-card-foreground shadow-sm">
        <LeagueSwitcher compact className="mb-2 border-b border-border px-2 pb-3 pt-1" />
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const active = isActive(tab.href);

          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted/70 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              <span>{tab.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
