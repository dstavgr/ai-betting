import Link from "next/link";
import { BarChart3, Gauge, Settings } from "lucide-react";

import { Button } from "@/components/ui/button";

const links = [
  { href: "/", label: "Matches", icon: Gauge },
  { href: "/research", label: "Research", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function MainNav() {
  return (
    <nav className="flex items-center gap-1" aria-label="Primary">
      {links.map((link) => {
        const Icon = link.icon;
        return (
          <Button key={link.href} asChild variant="ghost">
            <Link href={link.href}>
              <Icon className="h-4 w-4" aria-hidden="true" />
              {link.label}
            </Link>
          </Button>
        );
      })}
    </nav>
  );
}
