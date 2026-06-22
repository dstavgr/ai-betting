import type { Metadata } from "next";
import Link from "next/link";

import { MainNav } from "@/components/main-nav";

import "../styles/globals.css";

export const metadata: Metadata = {
  title: "Bet Analytics",
  description: "Soccer betting analytics for research and education.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <div className="min-h-screen bg-background text-foreground">
          <header className="border-b border-border bg-white">
            <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
              <LinkBrand />
              <MainNav />
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
          <footer className="border-t border-border bg-white">
            <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-muted-foreground">
              Research and education only. Not betting advice. No outcome is guaranteed. 21+.
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}

function LinkBrand() {
  return (
    <Link href="/" className="flex items-center gap-3">
      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
        BA
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-semibold">Bet Analytics</span>
        <span className="block text-xs text-muted-foreground">Greek Super League MVP</span>
      </span>
    </Link>
  );
}
