import { BarChart3, Beaker, Settings, ShieldCheck } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { EngineStatus } from "@/components/EngineStatus";
import { ResponsibleGamblingFooter } from "@/components/ResponsibleGamblingFooter";
import { Button } from "@/components/ui/button";
import type { EngineHealthResult } from "@/lib/api";

const navItems = [
  { href: "/", label: "Matches", icon: BarChart3 },
  { href: "/research", label: "Research", icon: Beaker },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({
  children,
  health,
}: {
  children: ReactNode;
  health: EngineHealthResult;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
        <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-card text-primary">
              <ShieldCheck className="h-5 w-5" />
            </span>
            <span className="flex flex-col">
              <span className="font-display text-base font-semibold leading-tight">
                Value terminal
              </span>
              <span className="text-xs text-muted-foreground">Greek Super League MVP</span>
            </span>
          </Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label="Main navigation">
            {navItems.map((item) => (
              <Button key={item.href} asChild variant="ghost" size="sm">
                <Link href={item.href}>
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Link>
              </Button>
            ))}
          </nav>
          <EngineStatus health={health} />
        </div>
        <nav className="grid grid-cols-3 border-t border-border md:hidden" aria-label="Mobile navigation">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center justify-center gap-2 px-3 py-3 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          ))}
        </nav>
      </header>
      <main className="flex-1 edge-grid">{children}</main>
      <ResponsibleGamblingFooter />
    </div>
  );
}
