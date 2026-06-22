export type LeagueConfig = {
  key: string;
  name: string;
  season: string;
};

export const leagues: readonly LeagueConfig[] = [
  {
    key: "gr-superleague",
    name: "Super League 1",
    season: "2025/26",
  },
] as const;

export type LeagueKey = LeagueConfig["key"];

export const defaultLeague = leagues[0];

export function getLeagueByKey(key: string | null | undefined): LeagueConfig {
  return leagues.find((league) => league.key === key) ?? defaultLeague;
}
