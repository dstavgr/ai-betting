import { describe, expect, it } from "vitest";
import { crestUrl } from "./crest";

describe("crestUrl", () => {
  it("builds the API-Sports CDN url from an id", () => {
    expect(crestUrl(645)).toBe("https://media.api-sports.io/football/teams/645.png");
  });

  it("returns null for missing ids", () => {
    expect(crestUrl(null)).toBeNull();
    expect(crestUrl(undefined)).toBeNull();
  });
});
