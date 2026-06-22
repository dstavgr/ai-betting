export function pct(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function signedPct(value: number, digits = 1): string {
  const formatted = pct(Math.abs(value), digits);
  return value >= 0 ? `+${formatted}` : `-${formatted}`;
}

export function odds(value: number): string {
  return value.toFixed(2);
}

export function shortDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function score(home: number | null, away: number | null): string {
  if (home === null || away === null) {
    return "-";
  }

  return `${home}-${away}`;
}
