import { describe, expect, it } from "vitest";
import { headToHead } from "./h2h";
import type { Fixture } from "./types";

function fx(
  home: string,
  away: string,
  goalsHome: number | null,
  goalsAway: number | null,
  kickoff: string,
  status = "FT",
): Fixture {
  return {
    id: Math.floor(Math.random() * 1e9),
    api_football_id: 0,
    kickoff_at: kickoff,
    league: "Super League 1",
    season: 2025,
    home_team: home,
    away_team: away,
    status_short: status,
    goals_home: goalsHome,
    goals_away: goalsAway,
  };
}

describe("headToHead", () => {
  it("counts wins from the current matchup perspective across both fixture orientations", () => {
    const fixtures = [
      fx("A", "B", 2, 0, "2026-01-01T00:00:00Z"),
      fx("B", "A", 1, 3, "2026-01-02T00:00:00Z"),
      fx("B", "A", 2, 1, "2026-01-03T00:00:00Z"),
    ];

    expect(headToHead(fixtures, "A", "B")).toMatchObject({
      homeWins: 2,
      draws: 0,
      awayWins: 1,
      total: 3,
    });

    expect(headToHead(fixtures, "B", "A")).toMatchObject({
      homeWins: 1,
      draws: 0,
      awayWins: 2,
      total: 3,
    });
  });

  it("counts draws separately", () => {
    const fixtures = [
      fx("A", "B", 1, 1, "2026-01-01T00:00:00Z"),
      fx("B", "A", 0, 0, "2026-01-02T00:00:00Z", "AET"),
      fx("A", "B", 3, 2, "2026-01-03T00:00:00Z", "PEN"),
    ];

    expect(headToHead(fixtures, "A", "B")).toMatchObject({
      homeWins: 1,
      draws: 2,
      awayWins: 0,
      total: 3,
    });
  });

  it("returns recent meetings in descending kickoff order and respects limit", () => {
    const fixtures = [
      fx("A", "B", 1, 0, "2026-01-01T00:00:00Z"),
      fx("B", "A", 2, 0, "2026-01-03T00:00:00Z"),
      fx("A", "B", 3, 3, "2026-01-02T00:00:00Z"),
    ];

    expect(headToHead(fixtures, "A", "B", { limit: 2 }).recent).toEqual([
      {
        kickoff: "2026-01-03T00:00:00Z",
        home: "B",
        away: "A",
        goalsHome: 2,
        goalsAway: 0,
      },
      {
        kickoff: "2026-01-02T00:00:00Z",
        home: "A",
        away: "B",
        goalsHome: 3,
        goalsAway: 3,
      },
    ]);
  });

  it("ignores unrelated, unfinished, and scoreless fixtures", () => {
    const fixtures = [
      fx("A", "B", 2, 1, "2026-01-01T00:00:00Z"),
      fx("A", "C", 4, 0, "2026-01-02T00:00:00Z"),
      fx("B", "A", null, null, "2026-01-03T00:00:00Z", "NS"),
      fx("A", "B", null, 1, "2026-01-04T00:00:00Z", "FT"),
    ];

    expect(headToHead(fixtures, "A", "B")).toMatchObject({
      homeWins: 1,
      draws: 0,
      awayWins: 0,
      total: 1,
      recent: [
        {
          kickoff: "2026-01-01T00:00:00Z",
          home: "A",
          away: "B",
          goalsHome: 2,
          goalsAway: 1,
        },
      ],
    });
  });
});
