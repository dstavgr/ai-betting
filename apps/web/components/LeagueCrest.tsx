"use client";

/* eslint-disable @next/next/no-img-element */

import { Trophy } from "lucide-react";
import { useState } from "react";

export function LeagueCrest({
  name,
  apiFootballId,
  size = 20,
}: {
  name: string;
  apiFootballId?: number | null;
  size?: number;
}) {
  const [failed, setFailed] = useState(false);
  const url = apiFootballId ? `https://media.api-sports.io/football/leagues/${apiFootballId}.png` : null;

  if (!url || failed) {
    return (
      <span
        className="flex shrink-0 items-center justify-center rounded-full border border-border bg-muted text-muted-foreground"
        style={{ width: size, height: size }}
        aria-label={name}
      >
        <Trophy className="size-3.5" aria-hidden="true" />
      </span>
    );
  }

  return (
    <img
      src={url}
      alt=""
      width={size}
      height={size}
      className="shrink-0 rounded-full"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
