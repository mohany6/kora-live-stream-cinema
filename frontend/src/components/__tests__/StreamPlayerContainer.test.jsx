import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Hls from "hls.js";

import StreamPlayerContainer from "../StreamPlayerContainer";

const iframeServers = [
  {
    id: "srv_1",
    server_name: "سيرفر 1 - متعدد الجودات",
    url: "https://live.example/embed/1",
    type: "iframe",
    is_active: true,
    sandbox: "allow-scripts allow-same-origin allow-presentation",
  },
  {
    id: "srv_2",
    server_name: "سيرفر 2 - يوتيوب",
    url: "https://www.youtube.com/embed/demo",
    type: "iframe",
    is_active: true,
  },
  {
    id: "srv_3",
    server_name: "سيرفر معطل",
    url: "https://live.example/embed/off",
    type: "iframe",
    is_active: false,
  },
];

describe("StreamPlayerContainer", () => {
  it("renders active server pills and loads the first server", () => {
    render(<StreamPlayerContainer servers={iframeServers} channel="beIN Sports 1" commentator="عصام الشوالي" />);

    expect(screen.getAllByRole("tab")).toHaveLength(2);
    expect(screen.getByTestId("server-pill-0")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("server-pill-1")).toHaveAttribute("aria-selected", "false");

    const iframe = screen.getByTestId("stream-iframe");
    expect(iframe).toHaveAttribute("src", "https://live.example/embed/1");
    expect(iframe).toHaveAttribute("sandbox", "allow-scripts allow-same-origin allow-presentation");
    expect(iframe).toHaveAttribute("referrerpolicy", "no-referrer");

    expect(screen.getByText(/القناة: beIN Sports 1/)).toBeInTheDocument();
    expect(screen.getByText(/المعلق: عصام الشوالي/)).toBeInTheDocument();
  });

  it("switches servers immediately when a pill is clicked", () => {
    render(<StreamPlayerContainer servers={iframeServers} />);

    fireEvent.click(screen.getByTestId("server-pill-1"));

    expect(screen.getByTestId("server-pill-1")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("stream-iframe")).toHaveAttribute(
      "src",
      "https://www.youtube.com/embed/demo",
    );
  });

  it("renders AlbaPlayer iframe with allow-forms sandbox and no-referrer policy", () => {
    const albaServers = [
      {
        id: "alba_1",
        server_name: "سيرفر 1 - AlbaPlayer",
        url: "https://24.shootinggames1.com/albaplayer/bein-sports-hd-1/?serv=0",
        type: "iframe",
        sandbox: "allow-forms allow-same-origin allow-scripts",
        is_active: true,
      },
    ];
    render(<StreamPlayerContainer servers={albaServers} channel="beIN SPORTS 1 HD" />);
    const iframe = screen.getByTestId("stream-iframe");
    expect(iframe).toHaveAttribute("src", "https://24.shootinggames1.com/albaplayer/bein-sports-hd-1/?serv=0");
    expect(iframe).toHaveAttribute("sandbox", expect.stringContaining("allow-forms"));
    expect(iframe).toHaveAttribute("referrerpolicy", "no-referrer");
  });

  it("auto-fails over to the next server when an HLS stream errors", () => {
    const servers = [
      {
        id: "hls",
        server_name: "سيرفر HLS",
        url: "https://cdn.example/live.m3u8",
        type: "m3u8",
        is_active: true,
      },
      {
        id: "backup",
        server_name: "سيرفر احتياطي",
        url: "https://backup.example/embed",
        type: "iframe",
        is_active: true,
      },
    ];

    render(<StreamPlayerContainer servers={servers} />);

    const video = screen.getByTestId("hls-player");
    expect(video).toHaveAttribute("src", "https://cdn.example/live.m3u8");

    fireEvent.error(video);

    expect(screen.getByTestId("server-pill-1")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("stream-iframe")).toHaveAttribute(
      "src",
      "https://backup.example/embed",
    );
    expect(screen.getByTestId("server-pill-0")).toHaveTextContent("تعذر");
  });

  it("shows an Arabic fallback with retry when every server fails", () => {
    const servers = [
      {
        id: "only",
        server_name: "السيرفر الوحيد",
        url: "https://cdn.example/only.m3u8",
        type: "m3u8",
        is_active: true,
      },
    ];

    render(<StreamPlayerContainer servers={servers} />);
    fireEvent.error(screen.getByTestId("hls-player"));

    const fallback = screen.getByTestId("stream-fallback");
    expect(fallback).toHaveTextContent("تعذر تشغيل البث");
    expect(screen.getByRole("button", { name: "إعادة المحاولة" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "إعادة المحاولة" }));
    expect(screen.getByTestId("hls-player")).toHaveAttribute("src", "https://cdn.example/only.m3u8");
  });

  it("renders an empty state when no active server exists", () => {
    render(<StreamPlayerContainer servers={[]} />);
    expect(screen.getByTestId("stream-empty")).toHaveTextContent("لا توجد سيرفرات متاحة حالياً");
    expect(screen.queryByTestId("stream-iframe")).not.toBeInTheDocument();
  });

  it("keeps the selected server and does not remount when servers array is refreshed with identical items", () => {
    const servers = [
      {
        id: "srv_1",
        server_name: "سيرفر 1",
        url: "https://live.example/embed/1",
        type: "iframe",
        is_active: true,
      },
      {
        id: "srv_2",
        server_name: "سيرفر 2",
        url: "https://live.example/embed/2",
        type: "iframe",
        is_active: true,
      },
    ];

    const { rerender } = render(<StreamPlayerContainer servers={servers} />);
    fireEvent.click(screen.getByTestId("server-pill-1"));

    expect(screen.getByTestId("server-pill-1")).toHaveAttribute("aria-selected", "true");
    const iframeBefore = screen.getByTestId("stream-iframe");
    expect(iframeBefore).toHaveAttribute("src", "https://live.example/embed/2");

    // Re-render with cloned array (simulating 30s poll)
    const clonedServers = servers.map((s) => ({ ...s }));
    rerender(<StreamPlayerContainer servers={clonedServers} />);

    expect(screen.getByTestId("server-pill-1")).toHaveAttribute("aria-selected", "true");
    const iframeAfter = screen.getByTestId("stream-iframe");
    expect(iframeAfter).toBe(iframeBefore);
  });

  it("uses hls.js when Hls.isSupported returns true and fails over on fatal HLS error", () => {
    let errorCallback = null;
    const mockLoadSource = vi.fn();
    const mockAttachMedia = vi.fn();
    const mockDestroy = vi.fn();
    const mockOn = vi.fn((event, cb) => {
      if (event === Hls.Events.ERROR) {
        errorCallback = cb;
      }
    });

    vi.spyOn(Hls, "isSupported").mockReturnValue(true);
    vi.spyOn(Hls.prototype, "loadSource").mockImplementation(mockLoadSource);
    vi.spyOn(Hls.prototype, "attachMedia").mockImplementation(mockAttachMedia);
    vi.spyOn(Hls.prototype, "destroy").mockImplementation(mockDestroy);
    vi.spyOn(Hls.prototype, "on").mockImplementation(mockOn);

    const servers = [
      {
        id: "hls-1",
        server_name: "سيرفر HLS رئيسي",
        url: "https://stream.example/live.m3u8",
        type: "m3u8",
        is_active: true,
      },
      {
        id: "iframe-2",
        server_name: "سيرفر احتياطي",
        url: "https://stream.example/backup",
        type: "iframe",
        is_active: true,
      },
    ];

    render(<StreamPlayerContainer servers={servers} />);

    expect(mockLoadSource).toHaveBeenCalledWith("https://stream.example/live.m3u8");
    expect(mockAttachMedia).toHaveBeenCalled();
    expect(errorCallback).toBeDefined();

    // Trigger fatal error
    act(() => {
      errorCallback(Hls.Events.ERROR, { fatal: true });
    });

    // Should fail over to backup iframe
    expect(screen.getByTestId("server-pill-1")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("stream-iframe")).toHaveAttribute("src", "https://stream.example/backup");
    expect(mockDestroy).toHaveBeenCalled();

    vi.restoreAllMocks();
  });

  it("renders quality selector options when playing an hls stream", () => {
    const servers = [
      {
        id: "s1",
        server_name: "سيرفر 1 - متعدد الجودات",
        url: "https://example.com/live.m3u8",
        type: "m3u8",
        is_active: true,
      },
    ];
    render(<StreamPlayerContainer servers={servers} channel="beIN 1" />);
    expect(screen.getByTestId("quality-selector")).toBeInTheDocument();
    expect(screen.getByText(/تلقائي|Auto/i)).toBeInTheDocument();
  });

  it("supports clappr stream type and allows quality level switching", () => {
    const servers = [
      {
        id: "clappr-1",
        server_name: "سيرفر Clappr Multi-Quality",
        url: "https://example.com/clappr.m3u8",
        type: "clappr",
        is_active: true,
      },
    ];
    render(<StreamPlayerContainer servers={servers} channel="beIN Sports 1" />);
    expect(screen.getByTestId("hls-player")).toBeInTheDocument();
    expect(screen.getByTestId("quality-selector")).toBeInTheDocument();

    const fhdBtn = screen.getByText(/1080p/i);
    expect(fhdBtn).toBeInTheDocument();
    fireEvent.click(fhdBtn);
    expect(fhdBtn).toHaveClass("bg-brand");
  });
});
