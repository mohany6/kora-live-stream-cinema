import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AdminPanel from "../AdminPanel";
import * as api from "../../lib/api";

const mockAdminMatch = {
  match: {
    id: "match_1",
    home_team: { name_ar: "ريال مدريد", name_en: "Real Madrid" },
    away_team: { name_ar: "برشلونة", name_en: "Barcelona" },
    league: { name_ar: "الدوري الإسباني", name_en: "La Liga" },
    status: "IN_PLAY",
    status_label_ar: "مباشر الآن",
    kickoff_time_utc: "2026-11-20T19:00:00Z",
    kickoff_time_local: "22:00",
    kickoff_date_local: "2026-11-20",
    home_score: 2,
    away_score: 1,
    elapsed_time: 65,
    is_admin_override: false,
    channel: "beIN Sports 1",
    commentator: "عصام الشوالي",
    competition_subtitle: "الدوري الإسباني",
  },
  servers: [
    {
      id: "srv_admin_1",
      server_name: "سيرفر الإدارة",
      url: "https://admin.example/stream1",
      type: "iframe",
      is_active: true,
      quality: "1080p",
    },
    {
      id: "srv_api_2",
      server_name: "سيرفر البث التلقائي",
      url: "https://api.example/stream2",
      type: "m3u8",
      is_active: true,
      quality: "720p",
    },
  ],
  admin_server_ids: ["srv_admin_1"],
  override: null,
};

describe("AdminPanel", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("prompts for admin token when unauthenticated and logs in on submit", async () => {
    vi.spyOn(api, "fetchAdminMatches").mockResolvedValueOnce({
      date: null,
      timezone: "Asia/Riyadh",
      timezone_label_ar: "بتوقيت مكة المكرمة",
      matches: [mockAdminMatch],
    });

    render(<AdminPanel onClose={vi.fn()} timezone="Asia/Riyadh" />);

    expect(screen.getByTestId("admin-token-input")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "تسجيل الدخول" })).toBeInTheDocument();

    fireEvent.change(screen.getByTestId("admin-token-input"), {
      target: { value: "secret-token" },
    });
    fireEvent.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    await waitFor(() => {
      expect(api.fetchAdminMatches).toHaveBeenCalledWith(
        "secret-token",
        expect.objectContaining({ tz: "Asia/Riyadh" }),
      );
    });

    expect(sessionStorage.getItem("kora-admin-token")).toBe("secret-token");
    expect(await screen.findByText("ريال مدريد")).toBeInTheDocument();
  });

  it("allows saving and clearing manual score override", async () => {
    sessionStorage.setItem("kora-admin-token", "secret-token");

    vi.spyOn(api, "fetchAdminMatches").mockResolvedValue({
      date: null,
      timezone: "Asia/Riyadh",
      timezone_label_ar: "بتوقيت مكة المكرمة",
      matches: [mockAdminMatch],
    });
    const saveSpy = vi.spyOn(api, "saveAdminOverride").mockResolvedValueOnce({});
    const clearSpy = vi.spyOn(api, "clearAdminOverride").mockResolvedValueOnce({});

    render(<AdminPanel onClose={vi.fn()} timezone="Asia/Riyadh" />);

    expect(await screen.findByText("ريال مدريد")).toBeInTheDocument();
    fireEvent.click(screen.getByText("ريال مدريد"));

    // Form inputs should show current match data
    const homeScoreInput = screen.getByTestId("override-home-score");
    fireEvent.change(homeScoreInput, { target: { value: "3" } });

    fireEvent.click(screen.getByRole("button", { name: "حفظ التعديل" }));

    await waitFor(() => {
      expect(saveSpy).toHaveBeenCalledWith(
        "secret-token",
        "match_1",
        expect.objectContaining({ home_score: 3 }),
      );
    });

    // Clear override button
    fireEvent.click(screen.getByRole("button", { name: "إلغاء التعديل" }));
    await waitFor(() => {
      expect(clearSpy).toHaveBeenCalledWith("secret-token", "match_1");
    });
  });

  it("allows adding and deleting stream servers", async () => {
    sessionStorage.setItem("kora-admin-token", "secret-token");

    vi.spyOn(api, "fetchAdminMatches").mockResolvedValue({
      date: null,
      timezone: "Asia/Riyadh",
      timezone_label_ar: "بتوقيت مكة المكرمة",
      matches: [mockAdminMatch],
    });
    const upsertSpy = vi.spyOn(api, "upsertAdminStream").mockResolvedValueOnce({ servers: [] });
    const deleteSpy = vi.spyOn(api, "deleteAdminStream").mockResolvedValueOnce({ servers: [] });

    render(<AdminPanel onClose={vi.fn()} timezone="Asia/Riyadh" />);

    expect(await screen.findByText("ريال مدريد")).toBeInTheDocument();
    fireEvent.click(screen.getByText("ريال مدريد"));

    // Add stream
    fireEvent.change(screen.getByTestId("stream-name-input"), {
      target: { value: "سيرفر خاص جديد" },
    });
    fireEvent.change(screen.getByTestId("stream-url-input"), {
      target: { value: "https://custom.example/live" },
    });
    fireEvent.click(screen.getByRole("button", { name: "إضافة سيرفر" }));

    await waitFor(() => {
      expect(upsertSpy).toHaveBeenCalledWith(
        "secret-token",
        "match_1",
        expect.objectContaining({
          server_name: "سيرفر خاص جديد",
          url: "https://custom.example/live",
        }),
      );
    });

    // Delete existing admin server
    const deleteBtn = screen.getByTestId("delete-stream-srv_admin_1");
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith("secret-token", "match_1", "srv_admin_1");
    });
  });

  it("allows switching to Ads CMS tab and viewing ads", async () => {
    sessionStorage.setItem("kora-admin-token", "secret-token");

    vi.spyOn(api, "fetchAdminMatches").mockResolvedValue({
      date: null,
      timezone: "Asia/Riyadh",
      timezone_label_ar: "بتوقيت مكة المكرمة",
      matches: [mockAdminMatch],
    });
    vi.spyOn(api, "fetchAdminAds").mockResolvedValue({
      ads: [
        {
          id: "ad-test-1",
          title: "إعلان بانر تجريبي",
          position: "header_top",
          ad_type: "image_banner",
          image_url: "https://example.com/ad.jpg",
          link_url: "https://example.com",
          target_device: "all",
          is_active: true,
          priority: 5,
        },
      ],
    });

    render(<AdminPanel onClose={vi.fn()} timezone="Asia/Riyadh" />);

    // Switch to Ads CMS Tab
    const adsTabBtn = await screen.findByRole("tab", { name: /إدارة الإعلانات/i });
    fireEvent.click(adsTabBtn);

    expect(await screen.findByText("إعلان بانر تجريبي")).toBeInTheDocument();
    expect(screen.getAllByText("ليدربورد علوي").length).toBeGreaterThan(0);
  });

  it("allows creating and toggling an ad in Ads CMS", async () => {
    sessionStorage.setItem("kora-admin-token", "secret-token");

    vi.spyOn(api, "fetchAdminMatches").mockResolvedValue({
      date: null,
      timezone: "Asia/Riyadh",
      timezone_label_ar: "بتوقيت مكة المكرمة",
      matches: [mockAdminMatch],
    });
    vi.spyOn(api, "fetchAdminAds").mockResolvedValue({
      ads: [
        {
          id: "ad-toggle-1",
          title: "إعلان للتفعيل",
          position: "player_bottom",
          ad_type: "image_banner",
          image_url: "https://example.com/ad.jpg",
          link_url: "https://example.com",
          target_device: "all",
          is_active: true,
          priority: 1,
        },
      ],
    });
    const toggleSpy = vi.spyOn(api, "toggleAdminAd").mockResolvedValue({ id: "ad-toggle-1", is_active: false });
    const createSpy = vi.spyOn(api, "createAdminAd").mockResolvedValue({
      id: "ad-new-1",
      title: "إعلان جديد",
      position: "header_top",
      ad_type: "image_banner",
      is_active: true,
    });

    render(<AdminPanel onClose={vi.fn()} timezone="Asia/Riyadh" />);

    // Switch to Ads CMS Tab
    const adsTabBtn = await screen.findByRole("tab", { name: /إدارة الإعلانات/i });
    fireEvent.click(adsTabBtn);

    expect(await screen.findByText("إعلان للتفعيل")).toBeInTheDocument();

    // Toggle active state
    const toggleBtn = screen.getByTestId("toggle-ad-ad-toggle-1");
    fireEvent.click(toggleBtn);
    await waitFor(() => {
      expect(toggleSpy).toHaveBeenCalledWith("secret-token", "ad-toggle-1");
    });

    // Open Add Ad Modal
    const addAdBtn = screen.getByRole("button", { name: /إضافة إعلان جديد/i });
    fireEvent.click(addAdBtn);

    fireEvent.change(screen.getByTestId("ad-title-input"), {
      target: { value: "إعلان جديد" },
    });
    fireEvent.change(screen.getByTestId("ad-image-url-input"), {
      target: { value: "https://example.com/new.png" },
    });
    fireEvent.click(screen.getByRole("button", { name: "حفظ الإعلان" }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        "secret-token",
        expect.objectContaining({
          title: "إعلان جديد",
          image_url: "https://example.com/new.png",
        }),
      );
    });
  });

  it("allows switching to Analytics tab and filtering stats by date periods", async () => {
    sessionStorage.setItem("kora-admin-token", "secret-token");

    vi.spyOn(api, "fetchAdminMatches").mockResolvedValue({
      date: null,
      timezone: "Asia/Riyadh",
      timezone_label_ar: "بتوقيت مكة المكرمة",
      matches: [mockAdminMatch],
    });
    const analyticsSpy = vi.spyOn(api, "fetchAdminAnalytics").mockResolvedValue({
      period: "week",
      summary: {
        today_visits: 1420,
        today_uniques: 980,
        week_visits: 8750,
        week_uniques: 5200,
        month_visits: 34100,
        month_uniques: 19800,
        year_visits: 210000,
        year_uniques: 95000,
        total_visits: 210000,
        total_uniques: 95000,
      },
      chart_data: [
        { date: "2026-11-20", label: "20/11", visits: 1420, uniques: 980 },
      ],
      device_stats: { mobile: 70, desktop: 28, tablet: 2 },
      top_pages: [
        { path: "/matches/today", visits: 5400, uniques: 3100 },
      ],
    });

    render(<AdminPanel onClose={vi.fn()} timezone="Asia/Riyadh" />);

    // Switch to Analytics Tab
    const analyticsTabBtn = await screen.findByRole("tab", { name: /إحصائيات/i });
    fireEvent.click(analyticsTabBtn);

    expect(await screen.findByText("إحصائيات الزوار والمنصة")).toBeInTheDocument();
    expect(screen.getAllByText("إجمالي الزيارات").length).toBeGreaterThan(0);
    expect(screen.getAllByText("الزوار الفريدون").length).toBeGreaterThan(0);

    // Switch period to Month
    const monthBtn = screen.getByRole("button", { name: /هذا الشهر/i });
    fireEvent.click(monthBtn);
    await waitFor(() => {
      expect(analyticsSpy).toHaveBeenCalledWith("secret-token", expect.objectContaining({ period: "month" }));
    });

    // Switch period to Year
    const yearBtn = screen.getByRole("button", { name: /هذا العام/i });
    fireEvent.click(yearBtn);
    await waitFor(() => {
      expect(analyticsSpy).toHaveBeenCalledWith("secret-token", expect.objectContaining({ period: "year" }));
    });
  });
});
