"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, Lightbulb, ListOrdered, Menu } from "lucide-react";

const tabs = [
  { href: "/", label: "Scores", icon: CalendarDays },
  { href: "/tips", label: "Tips", icon: Lightbulb },
  { href: "/table", label: "Table", icon: ListOrdered },
  { href: "/more", label: "More", icon: Menu },
];

export function BottomNav() {
  const pathname = usePathname();
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-50 grid grid-cols-4 border-t border-border bg-background/95 backdrop-blur md:mx-auto md:max-w-2xl"
      aria-label="Primary"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = isActive(tab.href);

        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`flex flex-col items-center gap-1 py-2 text-xs ${
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
