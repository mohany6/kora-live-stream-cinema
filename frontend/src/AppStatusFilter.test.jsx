import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import App from "./App";
import StreamPlayerContainer from "./components/StreamPlayerContainer";
import * as api from "./lib/api";

describe("Cloudflare SPA - Stream Cinema Match View & Blogger Bridge", () => {
  const mockMatches = [
    {
      id: "m-live-1",
      home_team: { name_ar: "ريال مدريد", logo_url: "" },
      away_team: { name_ar: "برشلونة", logo_url: "" },
      home_score: 2,
      away_score: 1,
      status: "IN_PLAY",
      status_label_ar: "مباشر الآن",
      elapsed_time: 75,
      live_minute_label: "75'",
      competition_subtitle: "الدوري الإسباني",
      league: { name_ar: "الدوري الإسباني" },
      kickoff_time_local: "22:00",
      has_stream: true,
      servers: [
        { id: "s1", server_name: "سيرفر 1 (HD)", url: "https://example.com/embed", type: "iframe" },
      ],
      home_lineup: [],
      away_lineup: [],
      events: [],
      stats: [],
      standings: [],
    },
  ];

  beforeEach(() => {
    vi.spyOn(api, "fetchActiveAds").mockResolvedValue({ ads: [] });
    vi.spyOn(api, "fetchTodayMatches").mockResolvedValue({
      matches: mockMatches,
      timezone_label_ar: "بتوقيت مكة المكرمة",
    });
    vi.spyOn(api, "fetchMatchDetail").mockResolvedValue({
      match: mockMatches[0],
      servers: mockMatches[0].servers,
      home_lineup: [],
      away_lineup: [],
      home_formation: "4-3-3",
      away_formation: "4-3-3",
      events: [],
      stats: [],
      standings: [],
    });
    vi.spyOn(api, "trackSiteVisit").mockResolvedValue({});
  });

  afterEach(() => {
    vi.restoreAllMocks();
    window.history.pushState(null, "", "/");
  });

  it("redirects root path to Blogger Hub where schedule lives", () => {
    window.history.pushState(null, "", "/");
    render(<App />);

    expect(screen.getByTestId("stream-cinema-redirect")).toBeInTheDocument();
    const redirectLink = screen.getByTestId("blogger-hub-redirect-link");
    expect(redirectLink).toHaveAttribute("href", "https://kora-live-to.blogspot.com");
  });

  it("renders the Blogger Hub bridge link in cinema header on /match/:id", async () => {
    window.history.pushState(null, "", "/match/m-live-1");
    render(<App />);

    const bloggerLink = await screen.findByTestId("blogger-hub-link");
    expect(bloggerLink).toBeInTheDocument();
    expect(bloggerLink).toHaveAttribute("href", "https://kora-live-to.blogspot.com");
    expect(bloggerLink).toHaveAttribute("target", "_blank");
  });

  it("renders the VIP 4K server link with Adsterra Smartlink in StreamPlayerContainer", () => {
    const servers = [
      { id: "s1", server_name: "سيرفر 1", url: "https://example.com/embed", type: "iframe" },
    ];
    render(<StreamPlayerContainer servers={servers} channel="beIN 1" commentator="عصام الشوالي" />);

    const vipLink = screen.getByTestId("server-vip-link");
    expect(vipLink).toBeInTheDocument();
    expect(vipLink).toHaveAttribute("href", "https://budgetezy.org/4/ae626546295ba9dbdec2ea24a521084c");
    expect(vipLink).toHaveAttribute("target", "_blank");
  });
});
