import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as api from "../../lib/api";
import MatchDetailHybrid from "../MatchDetailHybrid";
import { detailFixture, upcomingMatch } from "../../test/fixtures";

describe("MatchDetailHybrid", () => {
  beforeEach(() => {
    vi.spyOn(api, "fetchActiveAds").mockResolvedValue({ ads: [] });
  });

  it("renders the score header, broadcast metadata, stream player, and summary timeline", () => {
    render(<MatchDetailHybrid detail={detailFixture} onBack={vi.fn()} />);

    expect(screen.getByTestId("detail-score")).toHaveTextContent("2");
    expect(screen.getByTestId("detail-score")).toHaveTextContent("1");
    expect(screen.getByTestId("detail-live-badge")).toHaveTextContent("مباشر الآن");
    expect(screen.getByTestId("detail-live-badge")).toHaveTextContent("68'");

    expect(screen.getAllByText("ريال مدريد").length).toBeGreaterThan(0);
    expect(screen.getAllByText("برشلونة").length).toBeGreaterThan(0);
    expect(screen.getByTestId("stream-iframe")).toHaveAttribute(
      "src",
      "https://live.example/embed/1",
    );
    expect(screen.getAllByText(/الدوري الإسباني/).length).toBeGreaterThan(0);

    expect(screen.getByTestId("timeline")).toHaveTextContent("Kylian Mbappe");
    expect(screen.getByTestId("timeline")).toHaveTextContent("هدف افتتاحي لريال مدريد");
  });

  it("switches to the tactical pitch with Latin names and formations", () => {
    render(<MatchDetailHybrid detail={detailFixture} onBack={vi.fn()} />);

    fireEvent.click(screen.getByTestId("tab-lineup"));

    expect(screen.getByTestId("tab-lineup")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("tactical-pitch")).toBeInTheDocument();
    expect(screen.getAllByTestId("home-player")).toHaveLength(11);
    expect(screen.getAllByTestId("away-player")).toHaveLength(11);
    expect(screen.getByText("Thibaut Courtois")).toBeInTheDocument();
    expect(screen.getByText("Robert Lewandowski")).toBeInTheDocument();
    expect(screen.getByTestId("home-formation")).toHaveTextContent("4-3-3");
    expect(screen.getByTestId("away-formation")).toHaveTextContent("4-3-3");
  });

  it("renders comparative stats with Arabic labels and values", () => {
    render(<MatchDetailHybrid detail={detailFixture} onBack={vi.fn()} />);

    fireEvent.click(screen.getByTestId("tab-stats"));

    const panel = screen.getByTestId("stats-panel");
    expect(panel).toHaveTextContent("الاستحواذ");
    expect(panel).toHaveTextContent("58%");
    expect(panel).toHaveTextContent("42%");
    expect(panel).toHaveTextContent("التسديدات");
    expect(panel).toHaveTextContent("14");
    expect(panel).toHaveTextContent("9");
  });

  it("renders the standings table and highlights the match teams", () => {
    render(<MatchDetailHybrid detail={detailFixture} onBack={vi.fn()} />);

    fireEvent.click(screen.getByTestId("tab-standings"));

    const table = screen.getByTestId("standings-table");
    expect(within(table).getByText("ريال مدريد")).toBeInTheDocument();
    expect(within(table).getByText("برشلونة")).toBeInTheDocument();
    expect(within(table).getByText("31")).toBeInTheDocument();
    expect(within(table).getByText("(المضيف)")).toBeInTheDocument();
  });

  it("shows kickoff time and countdown for an upcoming match", () => {
    const scheduled = {
      ...detailFixture,
      match: { ...upcomingMatch, countdown_seconds: 11720 },
      servers: [],
      events: [],
    };

    render(<MatchDetailHybrid detail={scheduled} onBack={vi.fn()} />);

    expect(screen.getAllByText("21:00").length).toBeGreaterThan(0);
    expect(screen.getByText(/تبدأ بعد/)).toHaveTextContent("03:15:20");
    expect(screen.getByTestId("stream-empty")).toBeInTheDocument();
  });

  it("invokes the back handler", () => {
    const onBack = vi.fn();
    render(<MatchDetailHybrid detail={detailFixture} onBack={onBack} />);

    fireEvent.click(screen.getByTestId("back-button"));
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("does not render dead ad slots within match detail stream cinema", () => {
    render(<MatchDetailHybrid detail={detailFixture} onBack={vi.fn()} />);
    expect(screen.queryByTestId("ad-slot-sticky_bottom")).not.toBeInTheDocument();
    expect(screen.queryByTestId("ad-slot-header_top")).not.toBeInTheDocument();
  });
});
