import type { Fixture, Standing } from "./types";

const FINISHED = new Set(["FT", "AET", "PEN"]);

export function computeStandings(fixtures: Fixture[]): Standing[] {
  const rows = new Map<string, Standing>();
  const row = (team: string): Standing => {
    let r = rows.get(team);
    if (!r) {
      r = {
        team,
        played: 0,
        won: 0,
        drawn: 0,
        lost: 0,
        goalsFor: 0,
        goalsAgainst: 0,
        goalDiff: 0,
        points: 0,
      };
      rows.set(team, r);
    }
    return r;
  };

  for (const f of fixtures) {
    if (!f.status_short || !FINISHED.has(f.status_short)) continue;
    if (f.goals_home === null || f.goals_away === null || !f.home_team || !f.away_team) continue;

    const home = row(f.home_team);
    const away = row(f.away_team);

    home.played++;
    away.played++;
    home.goalsFor += f.goals_home;
    home.goalsAgainst += f.goals_away;
    away.goalsFor += f.goals_away;
    away.goalsAgainst += f.goals_home;

    if (f.goals_home > f.goals_away) {
      home.won++;
      home.points += 3;
      away.lost++;
    } else if (f.goals_home < f.goals_away) {
      away.won++;
      away.points += 3;
      home.lost++;
    } else {
      home.drawn++;
      away.drawn++;
      home.points++;
      away.points++;
    }
  }

  const table = [...rows.values()];
  for (const r of table) r.goalDiff = r.goalsFor - r.goalsAgainst;
  table.sort(
    (a, b) =>
      b.points - a.points ||
      b.goalDiff - a.goalDiff ||
      b.goalsFor - a.goalsFor ||
      a.team.localeCompare(b.team),
  );
  return table;
}
