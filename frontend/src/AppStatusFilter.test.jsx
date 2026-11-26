import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import App from "./App";
import StreamPlayerContainer from "./components/StreamPlayerContainer";
import * as api from "./lib/api";

describe("Cloudflare SPA Upgrades - Status Filter & Blogger Hub Bridge", () => {
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
    },
    {
      id: "m-upcoming-1",
      home_team: { name_ar: "ليفربول", logo_url: "" },
      away_team: { name_ar: "مانشستر سيتي", logo_url: "" },
      home_score: 0,
      away_score: 0,
      status: "SCHEDULED",
      status_label_ar: "لم تبدأ",
      countdown_seconds: 3600,
      competition_subtitle: "الدوري الإنجليزي",
      league: { name_ar: "الدوري الإنجليزي" },
      kickoff_time_local: "19:30",
      has_stream: false,
    },
    {
      id: "m-finished-1",
      home_team: { name_ar: "الأهلي", logo_url: "" },
      away_team: { name_ar: "الزمالك", logo_url: "" },
      home_score: 3,
      away_score: 0,
      status: "FINISHED",
      status_label_ar: "انتهت",
      competition_subtitle: "الدوري المصري",
      league: { name_ar: "الدوري المصري" },
      kickoff_time_local: "17:00",
      has_stream: false,
    },
  ];

  beforeEach(() => {
    vi.spyOn(api, "fetchActiveAds").mockResolvedValue({ ads: [] });
    vi.spyOn(api, "fetchTodayMatches").mockResolvedValue({
      matches: mockMatches,
      timezone_label_ar: "بتوقيت مكة المكرمة",
    });
    vi.spyOn(api, "trackSiteVisit").mockResolvedValue({});
  });

  it("renders status filter chips with correct counts and filters matches", async () => {
    render(<App />);

    // Wait for matches to load
    expect(await screen.findByTestId("status-filter-all")).toBeInTheDocument();
    expect(screen.getByTestId("status-filter-live")).toBeInTheDocument();
    expect(screen.getByTestId("status-filter-upcoming")).toBeInTheDocument();
    expect(screen.getByTestId("status-filter-finished")).toBeInTheDocument();

    // Verify all 3 match cards exist initially
    expect(screen.getByTestId("match-card-m-live-1")).toBeInTheDocument();
    expect(screen.getByTestId("match-card-m-upcoming-1")).toBeInTheDocument();
    expect(screen.getByTestId("match-card-m-finished-1")).toBeInTheDocument();

    // Filter by Live only
    fireEvent.click(screen.getByTestId("status-filter-live"));
    expect(screen.getByTestId("match-card-m-live-1")).toBeInTheDocument();
    expect(screen.queryByTestId("match-card-m-upcoming-1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("match-card-m-finished-1")).not.toBeInTheDocument();

    // Filter by Upcoming only
    fireEvent.click(screen.getByTestId("status-filter-upcoming"));
    expect(screen.queryByTestId("match-card-m-live-1")).not.toBeInTheDocument();
    expect(screen.getByTestId("match-card-m-upcoming-1")).toBeInTheDocument();
    expect(screen.queryByTestId("match-card-m-finished-1")).not.toBeInTheDocument();

    // Filter by Finished only
    fireEvent.click(screen.getByTestId("status-filter-finished"));
    expect(screen.queryByTestId("match-card-m-live-1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("match-card-m-upcoming-1")).not.toBeInTheDocument();
    expect(screen.getByTestId("match-card-m-finished-1")).toBeInTheDocument();

    // Reset to All
    fireEvent.click(screen.getByTestId("status-filter-all"));
    expect(screen.getByTestId("match-card-m-live-1")).toBeInTheDocument();
    expect(screen.getByTestId("match-card-m-upcoming-1")).toBeInTheDocument();
    expect(screen.getByTestId("match-card-m-finished-1")).toBeInTheDocument();
  });

  it("renders the Blogger Hub bridge link to kora-live-to.blogspot.com", async () => {
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
