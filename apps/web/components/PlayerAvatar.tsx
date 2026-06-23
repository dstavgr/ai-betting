"use client";

/* eslint-disable @next/next/no-img-element */

import { User } from "lucide-react";
import { useState } from "react";

export function PlayerAvatar({
  name,
  playerId,
  size = 28,
}: {
  name: string | null;
  playerId?: number | null;
  size?: number;
}) {
  const [failed, setFailed] = useState(false);
  const url = playerId ? `https://media.api-sports.io/football/players/${playerId}.png` : null;

  if (!url || failed) {
    return (
      <span
        className="flex shrink-0 items-center justify-center rounded-full border border-border bg-muted text-muted-foreground"
        style={{ width: size, height: size }}
        aria-label={name ?? "Player"}
      >
        <User className="size-3.5" aria-hidden="true" />
      </span>
    );
  }

  return (
    <img
      src={url}
      alt=""
      width={size}
      height={size}
      className="shrink-0 rounded-full object-cover"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
