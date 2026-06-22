import { describe, expect, it } from "vitest";
import { computeStandings } from "./standings";
import type { Fixture } from "./types";

function fx(home: string, away: string, gh: number, ga: number): Fixture {
  return {
    id: Math.floor(Math.random() * 1e9),
    api_football_id: 0,
    kickoff_at: "2026-01-01T00:00:00Z",
    league: "Super League 1",
    season: 2025,
    home_team: home,
    away_team: away,
    status_short: "FT",
    goals_home: gh,
    goals_away: ga,
  };
}

describe("computeStandings", () => {
  it("ranks by points, then goal difference", () => {
    const table = computeStandings([fx("A", "B", 2, 0), fx("B", "C", 1, 1), fx("C", "A", 0, 3)]);
    expect(table[0].team).toBe("A");
    expect(table[0].points).toBe(6);
    expect(table[0].goalDiff).toBe(5);
    const b = table.find((r) => r.team === "B")!;
    expect(b.points).toBe(1);
  });

  it("ignores non-finished fixtures", () => {
    const live = { ...fx("A", "B", 1, 0), status_short: "NS", goals_home: null, goals_away: null };
    expect(computeStandings([live])).toEqual([]);
  });
});
