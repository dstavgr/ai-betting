"use client";

import { useEffect, useMemo, useState } from "react";

import { cn } from "@/lib/utils";

type BookmakerIconProps = {
  bookmaker_slug: string | null | undefined;
  className?: string;
};

function normalizeSlug(slug: string | null | undefined): string {
  return (slug ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function humanizeBookmaker(slug: string | null | undefined): string {
  const cleaned = (slug ?? "").trim();

  if (!cleaned) {
    return "Bookmaker";
  }

  return cleaned
    .replace(/[_-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function BookmakerIcon({ bookmaker_slug, className }: BookmakerIconProps) {
  const slug = useMemo(() => normalizeSlug(bookmaker_slug), [bookmaker_slug]);
  const label = useMemo(() => humanizeBookmaker(bookmaker_slug), [bookmaker_slug]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [slug]);

  if (!slug || failed) {
    return (
      <span
        className={cn(
          "inline-flex h-7 max-w-32 items-center rounded-md border border-border bg-muted px-2 text-[11px] font-semibold text-muted-foreground",
          className,
        )}
      >
        <span className="truncate">{label}</span>
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex h-7 items-center rounded-md border border-border bg-background px-2",
        className,
      )}
      title={label}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/bookmakers/${slug}.svg`}
        alt={label}
        className="max-h-4 max-w-24 object-contain"
        loading="lazy"
        onError={() => setFailed(true)}
      />
    </span>
  );
}
