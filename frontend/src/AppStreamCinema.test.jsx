import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import StreamPlayerContainer from "./components/StreamPlayerContainer";
import MatchDetailHybrid from "./components/MatchDetailHybrid";
import { detailFixture, homeLineup, awayLineup } from "./test/fixtures";
import { localDateForOffset } from "./lib/api";

const BLOGGER_HUB_URL = "https://kora-live-to.blogspot.com";
const VIP_SMARTLINK_URL = "https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c";

function buildStaticMatchesPayload() {
  const todayStr = localDateForOffset(0, { timeZone: "Asia/Riyadh" });
  return {
    date: todayStr,
    timezone: "Asia/Riyadh",
    timezone_label_ar: "بتوقيت مكة المكرمة",
    updated_at: `${todayStr}T03:33:00Z`,
    count: 3,
    matches: [
      {
        id: "cinema-live-1",
        home_team: { id: "real", name_ar: "ريال مدريد", name_en: "Real Madrid", logo_url: null },
        away_team: { id: "barca", name_ar: "برشلونة", name_en: "Barcelona", logo_url: null },
        league: { id: "laliga", name_ar: "الدوري الإسباني", name_en: "La Liga", round: "الجولة 12" },
        status: "IN_PLAY",
        status_label_ar: "مباشر الآن",
        kickoff_time_utc: `${todayStr}T18:00:00Z`,
        kickoff_time_local: "21:00",
        kickoff_date_local: todayStr,
        home_score: 2,
        away_score: 1,
        elapsed_time: 72,
        live_minute_label: "72'",
        countdown_seconds: null,
        competition_subtitle: "الدوري الإسباني • الجولة 12",
        channel: "beIN SPORTS 1 HD",
        commentator: "عصام الشوالي",
        stadium: "سانتياغو برنابيو",
        has_stream: true,
        servers: [
          {
            id: "srv-1",
            server_name: "سيرفر 1 (HD)",
            url: "https://live.example/embed/clasico",
            type: "iframe",
            is_active: true,
          },
          {
            id: "srv-2",
            server_name: "سيرفر 2 (HLS)",
            url: "https://live.example/hls/clasico.m3u8",
            type: "m3u8",
            is_active: true,
          },
        ],
        home_lineup: homeLineup,
        away_lineup: awayLineup,
        home_formation: "4-3-3",
        away_formation: "4-3-3",
        events: detailFixture.events,
        stats: detailFixture.stats,
        standings: detailFixture.standings,
      },
      {
        id: "cinema-sched-2",
        home_team: { id: "hilal", name_ar: "الهلال", name_en: "Al Hilal", logo_url: null },
        away_team: { id: "nassr", name_ar: "النصر", name_en: "Al Nassr", logo_url: null },
        league: { id: "spl", name_ar: "دوري روشن السعودي", name_en: "Saudi Pro League" },
        status: "SCHEDULED",
        status_label_ar: "لم تبدأ",
        kickoff_time_utc: `${todayStr}T20:00:00Z`,
        kickoff_time_local: "23:00",
        kickoff_date_local: todayStr,
        home_score: 0,
        away_score: 0,
        countdown_seconds: 7200,
        competition_subtitle: "دوري روشن السعودي",
        channel: "SSC 1 HD",
        has_stream: false,
        servers: [],
        home_lineup: [],
        away_lineup: [],
        home_formation: null,
        away_formation: null,
        events: [],
        stats: [],
        standings: [],
      },
      {
        id: "cinema-fin-3",
        home_team: { id: "ahly", name_ar: "الأهلي", name_en: "Al Ahly", logo_url: null },
        away_team: { id: "zamalek", name_ar: "الزمالك", name_en: "Zamalek", logo_url: null },
        league: { id: "epl-eg", name_ar: "الدوري المصري", name_en: "Egyptian League" },
        status: "FINISHED",
        status_label_ar: "انتهت",
        kickoff_time_utc: `${todayStr}T14:00:00Z`,
        kickoff_time_local: "17:00",
        kickoff_date_local: todayStr,
        home_score: 3,
        away_score: 1,
        countdown_seconds: null,
        competition_subtitle: "الدوري المصري",
        has_stream: false,
        servers: [],
        home_lineup: [],
        away_lineup: [],
        home_formation: null,
        away_formation: null,
        events: [],
        stats: [],
        standings: [],
      },
    ],
  };
}

function mockFetchWithStaticMatches(payload = buildStaticMatchesPayload()) {
  const fetchMock = vi.fn(async (url) => {
    if (url === "/data/matches.json") {
      return {
        ok: true,
        json: async () => payload,
      };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("Pure Stream Cinema SPA (Live Cinema Player Only)", () => {
  beforeEach(() => {
    window.history.pushState(null, "", "/");
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    window.history.pushState(null, "", "/");
  });

  it("redirects root path / to Blogger Hub and never renders home schedule on pages.dev", () => {
    mockFetchWithStaticMatches();

    render(<App />);

    // Shows redirect screen
    expect(screen.getByTestId("stream-cinema-redirect")).toBeInTheDocument();
    const bloggerLink = screen.getByTestId("blogger-hub-redirect-link");
    expect(bloggerLink).toBeInTheDocument();
    expect(bloggerLink).toHaveAttribute("href", BLOGGER_HUB_URL);

    // Schedule, tabs, and match cards are NEVER mounted on pages.dev root
    expect(screen.queryByTestId("schedule-filter-tabs")).not.toBeInTheDocument();
    expect(screen.queryByTestId("match-card-cinema-live-1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("admin-panel-toggle")).not.toBeInTheDocument();
  });

  it("never mounts AdminPanel even when visiting /admin path", () => {
    window.history.pushState(null, "", "/admin");
    mockFetchWithStaticMatches();

    render(<App />);

    expect(screen.getByTestId("stream-cinema-redirect")).toBeInTheDocument();
    expect(screen.queryByTestId("admin-panel-toggle")).not.toBeInTheDocument();
    expect(screen.queryByTestId("admin-token-input")).not.toBeInTheDocument();
  });

  it("serves live stream cinema when visiting /match/:id with VIP 4K Smartlink and Blogger navigation", async () => {
    window.history.pushState(null, "", "/match/cinema-live-1");
    mockFetchWithStaticMatches();

    render(<App />);

    expect(await screen.findByTestId("match-detail")).toBeInTheDocument();
    expect(screen.getByTestId("stream-iframe")).toHaveAttribute(
      "src",
      "https://live.example/embed/clasico",
    );

    // VIP 4K Server Smartlink button
    const vipLink = screen.getByTestId("server-vip-link");
    expect(vipLink).toBeInTheDocument();
    expect(vipLink).toHaveTextContent("سيرفر VIP (4K بدون تقطيع)");
    expect(vipLink).toHaveAttribute("href", VIP_SMARTLINK_URL);
    expect(vipLink).toHaveAttribute("target", "_blank");

    // Header & detail Blogger Hub links
    const headerBloggerLink = screen.getByTestId("blogger-hub-link");
    expect(headerBloggerLink).toHaveAttribute("href", BLOGGER_HUB_URL);

    const detailBloggerLink = screen.getByTestId("detail-blogger-link");
    expect(detailBloggerLink).toHaveAttribute("href", BLOGGER_HUB_URL);

    // Back button returns to Blogger Hub
    const backButton = screen.getByTestId("back-button");
    expect(backButton).toBeInTheDocument();
  });

  it("always displays the VIP 4K Smartlink even when a match has zero scraped servers", () => {
    render(<StreamPlayerContainer servers={[]} channel="SSC 1 HD" />);

    expect(screen.getByTestId("stream-empty")).toBeInTheDocument();
    const vipLink = screen.getByTestId("server-vip-link");
    expect(vipLink).toBeInTheDocument();
    expect(vipLink).toHaveAttribute("href", VIP_SMARTLINK_URL);
    expect(vipLink).toHaveAttribute("target", "_blank");
  });

  it("renders MatchDetailHybrid back button and Blogger toolbar link", () => {
    const onBack = vi.fn();
    render(<MatchDetailHybrid detail={detailFixture} onBack={onBack} />);

    expect(screen.getByTestId("back-button")).toBeInTheDocument();
    const bloggerLink = screen.getByTestId("detail-blogger-link");
    expect(bloggerLink).toHaveAttribute("href", BLOGGER_HUB_URL);

    fireEvent.click(screen.getByTestId("back-button"));
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("never calls dead /api/v1/ads and supports direct /match/:id deep-link from static JSON", async () => {
    window.history.pushState(null, "", "/match/cinema-live-1");
    const fetchMock = mockFetchWithStaticMatches();

    render(<App />);
    expect(await screen.findByTestId("match-detail")).toBeInTheDocument();
    expect(screen.getByTestId("server-vip-link")).toBeInTheDocument();

    const adCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes("/api/v1/ads"));
    expect(adCalls).toHaveLength(0);

    const trackCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes("/api/v1/analytics/track"));
    expect(trackCalls).toHaveLength(0);

    window.history.pushState(null, "", "/");
  });
});
