export type LeagueConfig = {
  key: string;
  name: string;
  apiName: string;
  season: string;
  api_football_id: number;
};

export const leagues: readonly LeagueConfig[] = [
  {
    key: "gr-superleague",
    name: "Super League 1",
    apiName: "Super League 1",
    season: "2025/26",
    api_football_id: 197,
  },
  {
    key: "world-cup",
    name: "World Cup",
    apiName: "World Cup",
    season: "2026",
    api_football_id: 1,
  },
] as const;

export type LeagueKey = LeagueConfig["key"];

export const defaultLeague = leagues[0];

export function getLeagueByKey(key: string | null | undefined): LeagueConfig {
  return leagues.find((league) => league.key === key) ?? defaultLeague;
}

export function getLeagueByApiName(apiName: string | null | undefined): LeagueConfig | null {
  if (!apiName) return null;
  return leagues.find((league) => league.apiName === apiName || league.name === apiName) ?? null;
}
