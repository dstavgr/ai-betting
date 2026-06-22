const LIVE_STATUSES = new Set(["1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"]);

export function isLiveStatus(statusShort: string | null | undefined): boolean {
  return statusShort ? LIVE_STATUSES.has(statusShort) : false;
}

export function liveStatusLabel(statusShort: string | null | undefined): "HT" | "LIVE" | null {
  if (!isLiveStatus(statusShort)) {
    return null;
  }

  return statusShort === "HT" ? "HT" : "LIVE";
}
