import type { Fixture } from "./types";

type Result = "W" | "D" | "L";

const FINISHED_STATUSES = new Set(["FT", "AET", "PEN"]);

function resultForTeam(fixture: Fixture, teamName: string): Result | null {
  if (fixture.goals_home === null || fixture.goals_away === null) {
    return null;
  }

  const isHome = fixture.home_team === teamName;
  const isAway = fixture.away_team === teamName;

  if (!isHome && !isAway) {
    return null;
  }

  const goalsFor = isHome ? fixture.goals_home : fixture.goals_away;
  const goalsAgainst = isHome ? fixture.goals_away : fixture.goals_home;

  if (goalsFor > goalsAgainst) {
    return "W";
  }

  if (goalsFor < goalsAgainst) {
    return "L";
  }

  return "D";
}

export function teamForm(
  fixtures: Fixture[],
  teamName: string,
  opts?: { limit?: number },
): { results: Result[]; record: { w: number; d: number; l: number } } {
  const limit = Math.max(0, opts?.limit ?? 5);
  const results = fixtures
    .filter(
      (fixture) =>
        fixture.status_short !== null &&
        FINISHED_STATUSES.has(fixture.status_short) &&
        fixture.goals_home !== null &&
        fixture.goals_away !== null &&
        (fixture.home_team === teamName || fixture.away_team === teamName),
    )
    .sort((a, b) => new Date(b.kickoff_at).getTime() - new Date(a.kickoff_at).getTime())
    .slice(0, limit)
    .reverse()
    .map((fixture) => resultForTeam(fixture, teamName))
    .filter((result): result is Result => result !== null);

  return {
    results,
    record: {
      w: results.filter((result) => result === "W").length,
      d: results.filter((result) => result === "D").length,
      l: results.filter((result) => result === "L").length,
    },
  };
}
