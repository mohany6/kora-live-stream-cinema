import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  API_BASE,
  DISPLAY_TIMEZONE,
  SUPPORTED_TIMEZONES,
  fetchMatchDetail,
  fetchTodayMatches,
  localDateForOffset,
} from "../api";

describe("localDateForOffset", () => {
  it("uses Mecca time instead of the browser timezone", () => {
    // 02:36 UTC is still the previous evening in the Americas but already
    // November 19 in Mecca, which is the timezone shown in the UI.
    const now = new Date("2026-11-19T02:36:00Z");

    expect(localDateForOffset(0, { now })).toBe("2026-11-19");
    expect(localDateForOffset(1, { now })).toBe("2026-11-20");
    expect(localDateForOffset(-1, { now })).toBe("2026-11-18");
  });

  it("crosses month and year boundaries correctly", () => {
    const newYear = new Date("2026-12-31T21:30:00Z"); // 2027-01-01 00:30 in Mecca

    expect(localDateForOffset(0, { now: newYear })).toBe("2027-01-01");
    expect(localDateForOffset(-1, { now: newYear })).toBe("2026-12-31");
  });
});

describe("API helpers and timezones", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("exports SUPPORTED_TIMEZONES with expected Arabic labels", () => {
    expect(SUPPORTED_TIMEZONES).toBeDefined();
    const ids = SUPPORTED_TIMEZONES.map((tz) => tz.id);
    expect(ids).toContain("Asia/Riyadh");
    expect(ids).toContain("Africa/Cairo");
    expect(ids).toContain("Africa/Casablanca");
    expect(ids).toContain("Asia/Dubai");
    expect(ids).toContain("Europe/London");
    expect(ids).toContain("UTC");
  });

  it("fetchTodayMatches loads static /data/matches.json and localizes by date and tz", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        date: "2026-11-20",
        timezone: "Asia/Riyadh",
        timezone_label_ar: "بتوقيت مكة المكرمة",
        matches: [
          {
            id: "m-day",
            kickoff_time_utc: "2026-11-20T18:00:00Z",
            kickoff_date_local: "2026-11-20",
            kickoff_time_local: "21:00",
          },
          {
            id: "m-other",
            kickoff_time_utc: "2026-11-21T18:00:00Z",
            kickoff_date_local: "2026-11-21",
            kickoff_time_local: "21:00",
          },
        ],
      }),
    });

    const controller = new AbortController();
    const res = await fetchTodayMatches({
      date: "2026-11-20",
      tz: "Africa/Cairo",
      signal: controller.signal,
    });

    expect(fetch).toHaveBeenCalledWith(
      "/data/matches.json",
      expect.objectContaining({ signal: controller.signal }),
    );
    expect(res.timezone_label_ar).toBe("بتوقيت القاهرة");
    expect(res.matches).toHaveLength(1);
    expect(res.matches[0].id).toBe("m-day");
    expect(res.matches[0].kickoff_time_local).toBe("20:00");
  });

  it("fetchTodayMatches falls back to /api/v1/matches/today when static JSON is 404", async () => {
    fetch
      .mockResolvedValueOnce({ ok: false, status: 404 })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ matches: [] }),
      });

    const controller = new AbortController();
    await fetchTodayMatches({ date: "2026-11-20", tz: "Africa/Cairo", signal: controller.signal });

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/data/matches.json",
      expect.objectContaining({ signal: controller.signal }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      `${API_BASE}/api/v1/matches/today?date=2026-11-20&tz=Africa%2FCairo`,
      expect.objectContaining({ signal: controller.signal }),
    );
  });

  it("fetchMatchDetail constructs detail payload from static /data/matches.json when servers exist", async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        matches: [
          {
            id: "m1",
            kickoff_time_utc: "2026-11-20T18:00:00Z",
            servers: [{ id: "s1", server_name: "HD", url: "https://cdn.example/1", type: "iframe" }],
            events: [{ id: "e1", minute: 10, type: "goal", player_name: "Salah" }],
          },
        ],
      }),
    });

    const controller = new AbortController();
    const detail = await fetchMatchDetail("m1", { tz: "UTC", signal: controller.signal });

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith(
      "/data/matches.json",
      expect.objectContaining({ signal: controller.signal }),
    );
    expect(detail.match.id).toBe("m1");
    expect(detail.match.kickoff_time_local).toBe("18:00");
    expect(detail.servers).toHaveLength(1);
    expect(detail.home_formation).toBe("—");
    expect(detail.away_formation).toBe("—");
    expect(detail.events).toHaveLength(1);
  });

  it("fetchMatchDetail falls back to live match route when static JSON misses match", async () => {
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ matches: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ match: { id: "m1" } }),
      });

    const controller = new AbortController();
    await fetchMatchDetail("m1", { tz: "UTC", signal: controller.signal });

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/data/matches.json",
      expect.objectContaining({ signal: controller.signal }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      `${API_BASE}/api/v1/matches/m1?tz=UTC`,
      expect.objectContaining({ signal: controller.signal }),
    );
  });
});
