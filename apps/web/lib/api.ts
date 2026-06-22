import type { DataSummary, FeatureSnapshot, Fixture, FixtureDetail, FixtureOdds, Health, Match, Opportunity, Recommendation, ResearchSummary } from "./types";

const engineUrl = process.env.ENGINE_URL ?? "http://127.0.0.1:8000";

export type EngineHealthResult =
  | { ok: true; data: Health & { version: string } }
  | { ok: false; data: null };

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${engineUrl}${path}`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`Engine request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<Health | null> {
  try {
    return await fetchJson<Health>("/health");
  } catch {
    return null;
  }
}

export async function getEngineHealth(): Promise<EngineHealthResult> {
  const health = await getHealth();

  if (!health || health.status !== "ok") {
    return { ok: false, data: null };
  }

  return { ok: true, data: { ...health, version: health.version ?? "0.1.0" } };
}

export async function getMatches(): Promise<Match[]> {
  try {
    return await fetchJson<Match[]>("/matches");
  } catch {
    return [];
  }
}

export async function getOpportunities(limit = 12, ai = false): Promise<Opportunity[]> {
  try {
    return await fetchJson<Opportunity[]>(`/opportunities?limit=${limit}&ai=${ai}`);
  } catch {
    return [];
  }
}

export async function getFixtureOpportunity(id: string | number, ai = false): Promise<Opportunity | null> {
  try {
    return await fetchJson<Opportunity>(`/opportunities/${id}?ai=${ai}`);
  } catch {
    return null;
  }
}

export async function getResearch(): Promise<ResearchSummary | null> {
  try {
    return await fetchJson<ResearchSummary>("/research");
  } catch {
    return null;
  }
}

export async function getDataSummary(): Promise<DataSummary | null> {
  try {
    return await fetchJson<DataSummary>("/data/summary");
  } catch {
    return null;
  }
}

export async function getFixtures(limit = 24): Promise<Fixture[]> {
  try {
    return await fetchJson<Fixture[]>(`/data/fixtures?limit=${limit}`);
  } catch {
    return [];
  }
}

export async function getSeasonFixtures(): Promise<Fixture[]> {
  return getFixtures(500);
}

export async function getFixture(id: string | number): Promise<FixtureDetail | null> {
  try {
    return await fetchJson<FixtureDetail>(`/data/fixtures/${id}`);
  } catch {
    return null;
  }
}

export async function getFixtureFeatures(id: string | number): Promise<FeatureSnapshot | null> {
  try {
    return await fetchJson<FeatureSnapshot>(`/data/fixtures/${id}/features`);
  } catch {
    return null;
  }
}

export async function getFixtureOdds(id: string | number): Promise<FixtureOdds | null> {
  try {
    return await fetchJson<FixtureOdds>(`/data/fixtures/${id}/odds`);
  } catch {
    return null;
  }
}

export async function getFixtureRecommendations(id: string | number): Promise<Recommendation[]> {
  try {
    return await fetchJson<Recommendation[]>(`/data/fixtures/${id}/recommendations`);
  } catch {
    return [];
  }
}
