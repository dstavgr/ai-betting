import type {
  DataSummary,
  FeatureSnapshot,
  FixtureBetChatResponse,
  Fixture,
  FixtureDetail,
  FixtureMarkets,
  FixtureOdds,
  Health,
  Match,
  Opportunity,
  Recommendation,
  ResearchSummary,
  Team,
} from "./types";

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

async function postJson<T>(path: string, body: unknown, customHeaders?: Record<string, string>): Promise<T> {
  const response = await fetch(`${engineUrl}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: { Accept: "application/json", "Content-Type": "application/json", ...customHeaders },
    body: JSON.stringify(body),
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

export async function getTeams(): Promise<Team[]> {
  try {
    return await fetchJson<Team[]>("/data/teams");
  } catch {
    return [];
  }
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
    return await fetchJson<FixtureOdds>(`/data/fixtures/${id}/odds?limit=5000`);
  } catch {
    return null;
  }
}

export async function getFixtureMarkets(id: string | number): Promise<FixtureMarkets | null> {
  try {
    return await fetchJson<FixtureMarkets>("/data/fixtures/" + id + "/markets");
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

export async function askFixtureBetChat(
  id: string | number,
  question: string,
  forwardedFor?: string,
): Promise<FixtureBetChatResponse> {
  const headers = forwardedFor ? { "X-Forwarded-For": forwardedFor } : undefined;
  return postJson<FixtureBetChatResponse>(`/data/fixtures/${id}/bet-chat`, { question }, headers);
}
