import type { Fixture } from "./types";

export type HeadToHeadResult = {
  homeWins: number;
  draws: number;
  awayWins: number;
  total: number;
  recent: Array<{
    kickoff: string;
    home: string;
    away: string;
    goalsHome: number;
    goalsAway: number;
  }>;
};

const FINISHED_STATUSES = new Set(["FT", "AET", "PEN"]);

function isFinishedMeeting(fixture: Fixture, homeName: string, awayName: string): fixture is Fixture & {
  home_team: string;
  away_team: string;
  status_short: string;
  goals_home: number;
  goals_away: number;
} {
  const isSameMatchup =
    (fixture.home_team === homeName && fixture.away_team === awayName) ||
    (fixture.home_team === awayName && fixture.away_team === homeName);

  return (
    isSameMatchup &&
    fixture.status_short !== null &&
    FINISHED_STATUSES.has(fixture.status_short) &&
    fixture.goals_home !== null &&
    fixture.goals_away !== null
  );
}

export function headToHead(
  fixtures: Fixture[],
  homeName: string,
  awayName: string,
  opts: { limit?: number } = {},
): HeadToHeadResult {
  const meetings = fixtures
    .filter((fixture) => isFinishedMeeting(fixture, homeName, awayName))
    .sort((a, b) => Date.parse(b.kickoff_at) - Date.parse(a.kickoff_at));

  let homeWins = 0;
  let draws = 0;
  let awayWins = 0;

  for (const meeting of meetings) {
    if (meeting.goals_home === meeting.goals_away) {
      draws += 1;
      continue;
    }

    const winner = meeting.goals_home > meeting.goals_away ? meeting.home_team : meeting.away_team;

    if (winner === homeName) {
      homeWins += 1;
    } else if (winner === awayName) {
      awayWins += 1;
    }
  }

  const limit = Math.max(0, Math.floor(opts.limit ?? 5));

  return {
    homeWins,
    draws,
    awayWins,
    total: meetings.length,
    recent: meetings.slice(0, limit).map((meeting) => ({
      kickoff: meeting.kickoff_at,
      home: meeting.home_team,
      away: meeting.away_team,
      goalsHome: meeting.goals_home,
      goalsAway: meeting.goals_away,
    })),
  };
}
