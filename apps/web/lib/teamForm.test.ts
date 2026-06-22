import { describe, expect, it } from "vitest";
import { teamForm } from "./teamForm";
import type { Fixture } from "./types";

function fx(
  home: string,
  away: string,
  gh: number | null,
  ga: number | null,
  kickoff_at: string,
  status_short: string | null = "FT",
): Fixture {
  return {
    id: Number(kickoff_at.replace(/\D/g, "")),
    api_football_id: 0,
    kickoff_at,
    league: "Super League 1",
    season: 2025,
    home_team: home,
    away_team: away,
    status_short,
    goals_home: gh,
    goals_away: ga,
  };
}

describe("teamForm", () => {
  it("computes wins, draws, and losses in chronological order", () => {
    const form = teamForm(
      [
        fx("A", "B", 2, 0, "2026-01-03T00:00:00Z"),
        fx("A", "C", 1, 1, "2026-01-01T00:00:00Z"),
        fx("D", "A", 3, 1, "2026-01-02T00:00:00Z"),
      ],
      "A",
    );

    expect(form.results).toEqual(["D", "L", "W"]);
    expect(form.record).toEqual({ w: 1, d: 1, l: 1 });
  });

  it("uses the team perspective for home and away fixtures", () => {
    expect(teamForm([fx("A", "B", 1, 0, "2026-01-01T00:00:00Z")], "A").results).toEqual(["W"]);
    expect(teamForm([fx("A", "B", 1, 0, "2026-01-01T00:00:00Z")], "B").results).toEqual(["L"]);
  });

  it("limits to the most recent finished fixtures", () => {
    const form = teamForm(
      [
        fx("A", "B", 1, 0, "2026-01-01T00:00:00Z"),
        fx("A", "B", 0, 0, "2026-01-02T00:00:00Z"),
        fx("A", "B", 0, 2, "2026-01-03T00:00:00Z"),
      ],
      "A",
      { limit: 2 },
    );

    expect(form.results).toEqual(["D", "L"]);
    expect(form.record).toEqual({ w: 0, d: 1, l: 1 });
  });

  it("ignores unfinished fixtures and fixtures without final goals", () => {
    const form = teamForm(
      [
        fx("A", "B", 4, 0, "2026-01-01T00:00:00Z", "NS"),
        fx("A", "B", null, null, "2026-01-02T00:00:00Z", "FT"),
        fx("A", "B", 1, 0, "2026-01-03T00:00:00Z", "AET"),
        fx("A", "B", 2, 3, "2026-01-04T00:00:00Z", "PEN"),
      ],
      "A",
    );

    expect(form.results).toEqual(["W", "L"]);
    expect(form.record).toEqual({ w: 1, d: 0, l: 1 });
  });
});
