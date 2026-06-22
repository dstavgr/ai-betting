export type LeagueConfig = {
  key: string;
  name: string;
  apiName: string;
  season: string;
};

export const leagues: readonly LeagueConfig[] = [
  {
    key: "gr-superleague",
    name: "Super League 1",
    apiName: "Super League 1",
    season: "2025/26",
  },
  {
    key: "world-cup",
    name: "World Cup",
    apiName: "World Cup",
    season: "2026",
  },
] as const;

export type LeagueKey = LeagueConfig["key"];

export const defaultLeague = leagues[0];

export function getLeagueByKey(key: string | null | undefined): LeagueConfig {
  return leagues.find((league) => league.key === key) ?? defaultLeague;
}
