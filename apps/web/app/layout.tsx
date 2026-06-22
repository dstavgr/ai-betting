import type { Metadata } from "next";
import { Barlow, Barlow_Condensed } from "next/font/google";

import { BottomNav } from "@/components/BottomNav";
import { EngineStatusBanner } from "@/components/EngineStatusBanner";

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
  title: "Bet Analytics — Greek Super League",
  description: "Soccer match-center and betting research for the Greek Super League.",
  icons: {
    icon: "/favicon.svg",
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${barlow.variable} ${barlowCondensed.variable} font-sans antialiased`}>
        <div className="mx-auto flex min-h-screen max-w-2xl flex-col bg-background text-foreground">
          <header className="sticky top-0 z-40 border-b border-border bg-card/95 px-4 py-3 shadow-sm backdrop-blur">
            <span className="block font-display text-lg font-semibold leading-none tracking-normal">Super League 1</span>
            <span className="block text-xs text-muted-foreground">2025/26 · research, not advice</span>
          </header>
          <EngineStatusBanner />
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
