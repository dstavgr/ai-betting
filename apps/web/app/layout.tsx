import type { Metadata } from "next";

import { BottomNav } from "@/components/BottomNav";

import "../styles/globals.css";

export const metadata: Metadata = {
  title: "Bet Analytics — Greek Super League",
  description: "Soccer match-center and betting research for the Greek Super League.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <div className="mx-auto flex min-h-screen max-w-2xl flex-col bg-background text-foreground">
          <header className="sticky top-0 z-40 border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
            <span className="block text-sm font-semibold">Super League 1</span>
            <span className="block text-xs text-muted-foreground">2025/26 · research, not advice</span>
          </header>
          <main className="flex-1 px-4 py-4 pb-24">{children}</main>
          <footer className="px-4 pb-24 pt-2 text-center text-[11px] text-muted-foreground">
            Research and education only. Not betting advice. 21+.
          </footer>
          <BottomNav />
        </div>
      </body>
    </html>
  );
}
