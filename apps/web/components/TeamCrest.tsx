"use client";

/* eslint-disable @next/next/no-img-element */

import { Shield } from "lucide-react";
import { useState } from "react";

import { crestUrl } from "@/lib/crest";

export function TeamCrest({
  name,
  apiFootballId,
  size = 20,
}: {
  name: string;
  apiFootballId?: number | null;
  size?: number;
}) {
  const url = crestUrl(apiFootballId);
  const [failed, setFailed] = useState(false);

  if (!url || failed) {
    return (
      <span
        className="flex shrink-0 items-center justify-center rounded-full border border-border bg-muted text-[10px] font-semibold text-muted-foreground"
        style={{ width: size, height: size }}
        aria-label={name}
      >
        {name.trim() ? name.slice(0, 2).toUpperCase() : <Shield className="size-3" aria-hidden="true" />}
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
