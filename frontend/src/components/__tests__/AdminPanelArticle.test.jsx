import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AdminPanel from "../AdminPanel";
import * as api from "../../lib/api";

const mockAdminMatch = {
  match: {
    id: "match_clasico",
    home_team: { name_ar: "ريال مدريد", name_en: "Real Madrid" },
    away_team: { name_ar: "برشلونة", name_en: "Barcelona" },
    league: { name_ar: "الدوري الإسباني", name_en: "La Liga" },
    status: "SCHEDULED",
    status_label_ar: "لم تبدأ",
    kickoff_time_utc: "2026-11-24T20:00:00Z",
    kickoff_time_local: "23:00",
    kickoff_date_local: "2026-11-24",
    home_score: 0,
    away_score: 0,
    elapsed_time: null,
    is_admin_override: false,
    channel: "beIN Sports 1 HD",
    commentator: "حفيظ دراجي",
    competition_subtitle: "الدوري الإسباني",
  },
  servers: [],
  admin_server_ids: [],
  override: null,
};

describe("AdminPanel Blogger Article Generator", () => {
  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem("kora-admin-token", "valid-token");
    vi.spyOn(api, "fetchAdminMatches").mockResolvedValue({
      date: "2026-11-24",
      timezone: "Asia/Riyadh",
      matches: [mockAdminMatch],
    });
    vi.spyOn(api, "fetchAdminAds").mockResolvedValue({ total: 0, ads: [] });
    vi.spyOn(api, "fetchAdminAnalytics").mockResolvedValue({
      period: "week",
      summary: {},
      chart_data: [],
      device_stats: [],
      top_pages: [],
    });
    if (!navigator.clipboard) {
      navigator.clipboard = {
        writeText: vi.fn().mockResolvedValue(undefined),
      };
    } else {
      vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
    }
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders 'نسخ مقال التدوينة 📝' button and copies article to clipboard", async () => {
    vi.spyOn(api, "fetchAdminMatchArticle").mockResolvedValue({
      title: "مشاهدة مباراة ريال مدريد وبرشلونة",
      content: "<p>محتوى المقال</p>",
    });

    render(<AdminPanel onClose={vi.fn()} />);

    // Wait for match card to render
    await waitFor(() => {
      expect(screen.getByText("ريال مدريد")).toBeInTheDocument();
    });

    // Select the match
    fireEvent.click(screen.getByText("ريال مدريد"));

    // Find the article copy button
    const copyButton = await screen.findByTestId("copy-article-btn");
    expect(copyButton).toBeInTheDocument();

    // Click it
    fireEvent.click(copyButton);

    // Verify fetchAdminMatchArticle was called with match_clasico
    await waitFor(() => {
      expect(api.fetchAdminMatchArticle).toHaveBeenCalledWith("valid-token", "match_clasico", expect.any(String));
      expect(screen.getByText(/تم نسخ مقال Blogger/i)).toBeInTheDocument();
    });
  });

  it("falls back to document.execCommand when navigator.clipboard.writeText throws", async () => {
    vi.spyOn(api, "fetchAdminMatchArticle").mockResolvedValue({
      title: "مشاهدة مباراة ريال مدريد وبرشلونة",
      content: "<p>محتوى المقال البديل</p>",
    });

    // Make clipboard.writeText reject (e.g. NotAllowedError)
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("NotAllowedError"));
    document.execCommand = vi.fn().mockReturnValue(true);

    render(<AdminPanel onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("ريال مدريد")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("ريال مدريد"));
    const copyButton = await screen.findByTestId("copy-article-btn");
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(document.execCommand).toHaveBeenCalledWith("copy");
      expect(screen.getByText(/تم نسخ مقال Blogger/i)).toBeInTheDocument();
    });
  });
});
