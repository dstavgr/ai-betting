import type { Metadata } from "next";
import { Barlow, Barlow_Condensed } from "next/font/google";
import { Suspense } from "react";

import { BottomNav, SidebarNav } from "@/components/BottomNav";
import { EngineStatusBanner } from "@/components/EngineStatusBanner";
import { LeagueCrest } from "@/components/LeagueCrest";
import { LeagueSwitcher } from "@/components/LeagueSwitcher";
import { defaultLeague } from "@/lib/leagues";

import "../styles/globals.css";

const barlow = Barlow({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

const barlowCondensed = Barlow_Condensed({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Bet AI — Football match-center & betting research",
  description: "Bet AI: AI-assisted football match-center, odds, and betting research. Research and education only.",
  icons: {
    icon: "/favicon.svg",
  },
};

function LeagueSwitcherFallback() {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <LeagueCrest name={defaultLeague.name} apiFootballId={defaultLeague.api_football_id} size={26} />
      <div className="min-w-0">
        <span className="block truncate font-display text-lg font-semibold leading-none tracking-normal">
          {defaultLeague.name}
        </span>
        <span className="block truncate text-xs text-muted-foreground">
          {defaultLeague.season} &middot; research, not advice
        </span>
      </div>
    </div>
  );
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${barlow.variable} ${barlowCondensed.variable} font-sans antialiased`}>
        <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col bg-background text-foreground md:max-w-5xl">
          <header className="sticky top-0 z-40 border-b border-border bg-card/95 px-4 py-3 backdrop-blur md:px-5">
            <span className="mb-1 block font-display text-base font-extrabold uppercase tracking-tight">Bet<span className="text-primary">AI</span></span>
            <Suspense fallback={<LeagueSwitcherFallback />}>
              <LeagueSwitcher />
            </Suspense>
          </header>
          <EngineStatusBanner />
          <div className="flex flex-1 md:gap-3 md:px-5 md:py-4 lg:gap-4">
            <Suspense fallback={null}>
              <SidebarNav />
            </Suspense>
            <div className="flex min-w-0 flex-1 flex-col">
              <main className="flex-1 px-4 py-4 pb-24 md:px-0 md:py-0 md:pb-0">{children}</main>
              <footer className="px-4 pb-24 pt-2 text-center text-[11px] text-muted-foreground md:px-0 md:pb-1 md:pt-6">
                Research and education only. Not betting advice. 21+.
              </footer>
            </div>
          </div>
          <Suspense fallback={null}>
            <BottomNav />
          </Suspense>
        </div>
      </body>
    </html>
  );
}
