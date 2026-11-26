import { describe, expect, it } from "vitest";
import { getMatchIdFromPath } from "./App";

describe("getMatchIdFromPath", () => {
  it("extracts match ID from standard /match/123 path", () => {
    expect(getMatchIdFromPath("/match/401915378")).toBe("401915378");
  });

  it("extracts match ID with trailing slash", () => {
    expect(getMatchIdFromPath("/match/barca-vs-sabah/")).toBe("barca-vs-sabah");
  });

  it("returns null for root or unrelated paths", () => {
    expect(getMatchIdFromPath("/")).toBeNull();
    expect(getMatchIdFromPath("/admin")).toBeNull();
  });
});

