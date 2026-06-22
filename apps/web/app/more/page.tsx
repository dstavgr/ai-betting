import Link from "next/link";

const links = [
  { href: "/research", label: "Research & backtest" },
  { href: "/settings", label: "Settings" },
];

export default function MorePage() {
  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">More</h1>
      <ul className="divide-y divide-border rounded-md border border-border">
        {links.map((l) => (
          <li key={l.href}>
            <Link href={l.href} className="block px-4 py-3 text-sm">
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
      <p className="px-1 text-[11px] text-muted-foreground">Research and education only. Not betting advice. 21+.</p>
    </div>
  );
}
