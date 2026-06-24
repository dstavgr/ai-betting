"use client";

import { useEffect, useState } from "react";
import { Newspaper, ExternalLink, ShieldAlert, Loader2 } from "lucide-react";

import { SectionCard } from "@/components/ui/section-card";
import type { FixtureNews, NewsBundle } from "@/lib/types";
import { cn } from "@/lib/utils";

interface NewsPanelProps {
  fixtureId: number;
  initialNews?: FixtureNews | null;
}

function getTierBadgeStyles(tier: string) {
  switch (tier) {
    case "OFFICIAL_CLUB":
    case "OFFICIAL_LEAGUE":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
    case "VERIFIED_JOURNALIST":
    case "ESTABLISHED_MEDIA":
      return "border-zinc-700 bg-zinc-800/40 text-zinc-300";
    case "AGGREGATOR":
    case "FAN_COMMUNITY":
    case "RUMOUR":
      return "border-amber-500/30 bg-amber-500/10 text-amber-400";
    default:
      return "border-zinc-800 bg-zinc-900/50 text-zinc-400";
  }
}

function formatTierName(tier: string) {
  return tier
    .split("_")
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(" ");
}

function formatDirection(direction: string) {
  switch (direction) {
    case "LEAN_HOME":
      return "Lean Home";
    case "LEAN_DRAW":
      return "Lean Draw";
    case "LEAN_AWAY":
      return "Lean Away";
    default:
      return "Neutral";
  }
}

export function NewsPanel({ fixtureId, initialNews }: NewsPanelProps) {
  const [news, setNews] = useState<FixtureNews | null>(initialNews ?? null);
  const [loading, setLoading] = useState(!initialNews);

  useEffect(() => {
    if (initialNews) {
      setNews(initialNews);
      setLoading(false);
      return;
    }

    let active = true;
    async function loadNews() {
      try {
        setLoading(true);
        const res = await fetch(`/api/fixture-news?fixtureId=${fixtureId}`);
        if (!res.ok) throw new Error("Failed to load news");
        const data = await res.json();
        if (active) {
          setNews(data);
        }
      } catch {
        // Fallback or empty state
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadNews();
    return () => {
      active = false;
    };
  }, [fixtureId, initialNews]);

  if (loading) {
    return (
      <SectionCard
        title={
          <span className="inline-flex items-center gap-1.5">
            <Newspaper className="size-3.5" aria-hidden="true" />
            News signal
          </span>
        }
        className="min-w-0"
      >
        <div className="flex h-32 items-center justify-center gap-1.5 text-xs text-muted-foreground">
          <Loader2 className="size-4 animate-spin text-primary" />
          <span>Ingesting news signals...</span>
        </div>
      </SectionCard>
    );
  }

  const homeArticles = news?.home_bundle?.articles || [];
  const awayArticles = news?.away_bundle?.articles || [];
  const totalArticles = homeArticles.length + awayArticles.length;
  const emptyState = totalArticles === 0;

  const disclaimerText =
    news?.disclaimer ||
    news?.news_adjusted?.disclaimer ||
    "News-informed independent signal only; NOT walk-forward-validated; not betting advice.";

  function renderTeamSection(bundle: NewsBundle, role: "Home" | "Away") {
    const articles = bundle.articles || [];
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between border-b border-border pb-1">
          <h3 className="font-display text-sm font-semibold tracking-wide text-foreground">
            {bundle.team} <span className="text-xs font-normal text-muted-foreground">({role})</span>
          </h3>
          {news?.news_adjusted?.per_team_summary?.[bundle.team] && (
            <span className="text-[11px] font-mono text-muted-foreground">
              Score: {Number(news.news_adjusted.per_team_summary[bundle.team].news_score).toFixed(2)}
            </span>
          )}
        </div>

        {bundle.top_signals && bundle.top_signals.length > 0 && (
          <div className="space-y-1">
            {bundle.top_signals.map((signal, idx) => (
              <div
                key={idx}
                className="flex items-start gap-1.5 rounded border border-amber-500/10 bg-amber-500/5 px-2 py-1 text-xs text-amber-300"
              >
                <span className="mt-0.5 select-none text-[10px] font-bold">•</span>
                <span>{signal}</span>
              </div>
            ))}
          </div>
        )}

        {articles.length === 0 ? (
          <p className="text-xs text-muted-foreground">No articles for this team.</p>
        ) : (
          <div className="space-y-2">
            {articles.map((article, artIndex) => (
              <article
                key={artIndex}
                className="group relative rounded border border-border/60 bg-muted/10 p-2.5 transition-colors hover:bg-muted/20"
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <span
                    className={cn(
                      "rounded border px-1.5 py-0.5 text-[9px] font-semibold tracking-[0.05em] uppercase leading-none",
                      getTierBadgeStyles(article.source_tier)
                    )}
                  >
                    {formatTierName(article.source_tier)}
                  </span>
                  <span className="text-[10px] font-semibold uppercase tracking-[0.05em] text-muted-foreground/80">
                    {article.category}
                  </span>
                  <span className="ml-auto text-[10px] font-mono text-muted-foreground/60">
                    W: {article.weight.toFixed(2)}
                  </span>
                </div>

                <h4 className="mt-1.5 text-xs font-semibold leading-normal text-foreground group-hover:text-primary">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 hover:underline"
                  >
                    {article.title}
                    <ExternalLink className="size-3 shrink-0 text-muted-foreground/60 group-hover:text-primary" />
                  </a>
                </h4>

                <p className="mt-1 text-xs leading-relaxed text-muted-foreground line-clamp-2">
                  {article.summary}
                </p>

                <div className="mt-2 h-0.5 w-full overflow-hidden rounded-full bg-border">
                  <div
                    className="h-full bg-primary/70"
                    style={{ width: `${article.weight * 100}%` }}
                  />
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <SectionCard
      title={
        <span className="inline-flex items-center gap-1.5">
          <Newspaper className="size-3.5" aria-hidden="true" />
          News signal
        </span>
      }
      className="min-w-0"
    >
      {/* Prominent warning banner */}
      <div className="mb-3 rounded-lg border border-red-500/20 bg-red-950/20 px-3 py-2 text-xs text-red-400">
        <div className="flex items-center gap-1.5 font-semibold uppercase tracking-wider">
          <ShieldAlert className="size-3.5" />
          <span>Research signal — not betting advice, not model-validated.</span>
        </div>
        {disclaimerText && <div className="mt-1 text-muted-foreground">{disclaimerText}</div>}
      </div>

      {emptyState ? (
        <p className="py-4 text-center text-xs text-muted-foreground">
          No team-news signals available for this fixture.
        </p>
      ) : (
        <>
          {/* Subtle lean chip */}
          {news?.news_adjusted && (
            <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-border bg-background/50 px-3 py-2 text-xs">
              <div className="min-w-0">
                <span className="font-medium text-muted-foreground">Direction Lean: </span>
                <span className="font-semibold uppercase tracking-wide text-foreground">
                  {formatDirection(news.news_adjusted.suggested_direction)}
                </span>
                {news.news_adjusted.confidence > 0 && (
                  <span className="ml-1 font-mono text-[11px] text-muted-foreground">
                    (Conf: {(news.news_adjusted.confidence * 100).toFixed(0)}%)
                  </span>
                )}
              </div>
              <div className="shrink-0 font-semibold uppercase tracking-wider text-[10px] text-muted-foreground">
                Independent signal
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {news?.home_bundle && renderTeamSection(news.home_bundle, "Home")}
            {news?.away_bundle && renderTeamSection(news.away_bundle, "Away")}
          </div>
        </>
      )}
    </SectionCard>
  );
}
