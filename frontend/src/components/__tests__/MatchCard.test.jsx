import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import MatchCard from "../MatchCard";
import { finishedMatch, liveMatch, postponedMatch, upcomingMatch } from "../../test/fixtures";

describe("MatchCard", () => {
  it("uses an RTL structure with the home team inline-start and away team inline-end", () => {
    render(<MatchCard match={liveMatch} />);

    const card = screen.getByTestId("match-card-match_live");
    expect(card).toHaveAttribute("dir", "rtl");

    const home = screen.getByTestId("home-team");
    const away = screen.getByTestId("away-team");
    expect(home).toHaveTextContent("ريال مدريد");
    expect(away).toHaveTextContent("برشلونة");

    // In RTL the first DOM node renders on the right, so home must precede away.
    expect(home.compareDocumentPosition(away) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("renders a live score, pulsing red badge, minute, and competition subtitle", () => {
    render(<MatchCard match={liveMatch} />);

    expect(screen.getByTestId("score")).toHaveTextContent("2");
    expect(screen.getByTestId("score")).toHaveTextContent("1");

    const badge = screen.getByTestId("live-badge");
    expect(badge).toHaveTextContent("مباشر الآن");
    expect(badge).toHaveTextContent("68'");
    expect(badge).toHaveClass("animate-live-pulse");

    expect(screen.getByText("الدوري الإسباني • الجولة 12")).toBeInTheDocument();
  });

  it("renders the green countdown and kickoff time for an upcoming match", () => {
    render(<MatchCard match={upcomingMatch} />);

    expect(screen.getByText("21:00")).toBeInTheDocument();
    const countdown = screen.getByTestId("countdown-badge");
    expect(countdown).toHaveTextContent("تبدأ بعد");
    expect(countdown).toHaveTextContent("03:15:20");
    expect(screen.queryByTestId("live-badge")).not.toBeInTheDocument();
  });

  it("renders the finished and postponed states without a countdown", () => {
    const { rerender } = render(<MatchCard match={finishedMatch} />);
    expect(screen.getByTestId("finished-badge")).toHaveTextContent("انتهت");
    expect(screen.getByTestId("score")).toHaveTextContent("1");
    expect(screen.queryByTestId("countdown-badge")).not.toBeInTheDocument();

    rerender(<MatchCard match={postponedMatch} />);
    expect(screen.getByTestId("postponed-badge")).toHaveTextContent("مؤجلة");
    expect(screen.queryByTestId("live-badge")).not.toBeInTheDocument();
    expect(screen.queryByTestId("countdown-badge")).not.toBeInTheDocument();
  });

  it("opens the match on click and with the keyboard", () => {
    const onSelect = vi.fn();
    render(<MatchCard match={liveMatch} onSelect={onSelect} />);

    const card = screen.getByTestId("match-card-match_live");
    fireEvent.click(card);
    expect(onSelect).toHaveBeenCalledWith(liveMatch);

    fireEvent.keyDown(card, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledTimes(2);
  });

  it("falls back to the Arabic initial when a crest is missing", () => {
    render(<MatchCard match={liveMatch} />);
    const home = screen.getByTestId("home-team");
    expect(home).toHaveTextContent("ر");
    expect(home.querySelector("img")).toBeNull();
  });

  it("ticks the countdown timer down each second", () => {
    vi.useFakeTimers();
    render(<MatchCard match={upcomingMatch} />);

    expect(screen.getByTestId("countdown-badge")).toHaveTextContent("03:15:20");

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(screen.getByTestId("countdown-badge")).toHaveTextContent("03:15:18");
    vi.useRealTimers();
  });

  it("renders distinct Arabic halftime badge for HALFTIME status", () => {
    const halftimeMatch = {
      ...liveMatch,
      status: "HALFTIME",
      live_minute_label: "استراحة",
    };
    render(<MatchCard match={halftimeMatch} />);

    expect(screen.getByTestId("halftime-badge")).toHaveTextContent("استراحة");
    expect(screen.queryByTestId("live-badge")).not.toBeInTheDocument();
  });

  it("renders broadcast channel when provided on the match", () => {
    render(<MatchCard match={liveMatch} />);
    const channelBadge = screen.getByTestId("match-channel");
    expect(channelBadge).toBeInTheDocument();
    expect(channelBadge).toHaveTextContent("beIN Sports 1");
  });

  it("renders stream status notice or available badge based on has_stream", () => {
    const { rerender } = render(<MatchCard match={upcomingMatch} />);
    const notice = screen.getByTestId("stream-status");
    expect(notice).toHaveTextContent("سيتم تحديث روابط البث قبل انطلاق المباراة");

    rerender(<MatchCard match={liveMatch} />);
    const available = screen.getByTestId("stream-status");
    expect(available).toHaveTextContent("البث المباشر متاح");
  });
});
