import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdSlot from "../AdSlot";
import * as api from "../../lib/api";

describe("AdSlot", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders image banner with link, sponsor label, and proper attributes", async () => {
    vi.spyOn(api, "fetchActiveAds").mockResolvedValue({
      ads: [
        {
          id: "ad-1",
          title: "Sponsor Banner",
          position: "header_top",
          ad_type: "image_banner",
          image_url: "https://example.com/banner.jpg",
          link_url: "https://example.com/target",
          target_device: "all",
          is_active: true,
          priority: 10,
        },
      ],
    });

    render(<AdSlot position="header_top" />);

    await waitFor(() => {
      expect(screen.getByAltText("Sponsor Banner")).toBeInTheDocument();
    });

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "https://example.com/target");
    expect(link).toHaveAttribute("target", "_blank");
    expect(screen.getByText("إعلان")).toBeInTheDocument();
  });

  it("renders custom HTML snippet safely", async () => {
    vi.spyOn(api, "fetchActiveAds").mockResolvedValue({
      ads: [
        {
          id: "ad-html",
          title: "HTML Ad",
          position: "player_bottom",
          ad_type: "custom_html",
          html_code: "<div data-testid='custom-ad-content'>Sponsored Content</div>",
          target_device: "all",
          is_active: true,
          priority: 5,
        },
      ],
    });

    render(<AdSlot position="player_bottom" />);

    await waitFor(() => {
      expect(screen.getByTestId("custom-ad-content")).toHaveTextContent("Sponsored Content");
    });
  });

  it("renders nothing (null) when no ads exist for the position", async () => {
    vi.spyOn(api, "fetchActiveAds").mockResolvedValue({ ads: [] });

    const { container } = render(<AdSlot position="in_feed" />);

    await waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });

  it("handles dismissal of sticky_bottom ad when close button is clicked", async () => {
    vi.spyOn(api, "fetchActiveAds").mockResolvedValue({
      ads: [
        {
          id: "ad-sticky",
          title: "Sticky Ad",
          position: "sticky_bottom",
          ad_type: "image_banner",
          image_url: "https://example.com/sticky.jpg",
          link_url: "https://example.com",
          target_device: "all",
          is_active: true,
          priority: 100,
        },
      ],
    });

    render(<AdSlot position="sticky_bottom" />);

    await waitFor(() => {
      expect(screen.getByAltText("Sticky Ad")).toBeInTheDocument();
    });

    const closeBtn = screen.getByRole("button", { name: /إغلاق/i });
    expect(closeBtn).toBeInTheDocument();

    fireEvent.click(closeBtn);

    expect(screen.queryByAltText("Sticky Ad")).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem("kora_sticky_ad_dismissed")).toBe("true");
  });

  it("does not render sticky_bottom ad if already dismissed in sessionStorage", async () => {
    window.sessionStorage.setItem("kora_sticky_ad_dismissed", "true");
    vi.spyOn(api, "fetchActiveAds").mockResolvedValue({
      ads: [
        {
          id: "ad-sticky-2",
          title: "Sticky Ad 2",
          position: "sticky_bottom",
          ad_type: "image_banner",
          image_url: "https://example.com/sticky.jpg",
          link_url: "https://example.com",
          target_device: "all",
          is_active: true,
          priority: 100,
        },
      ],
    });

    const { container } = render(<AdSlot position="sticky_bottom" />);
    expect(container.firstChild).toBeNull();
    window.sessionStorage.removeItem("kora_sticky_ad_dismissed");
  });

  it("applies responsive classes for mobile and desktop target_device", async () => {
    vi.spyOn(api, "fetchActiveAds").mockResolvedValue({
      ads: [
        {
          id: "ad-mobile",
          title: "Mobile Only",
          position: "player_top",
          ad_type: "image_banner",
          image_url: "https://example.com/mobile.jpg",
          target_device: "mobile",
          is_active: true,
        },
      ],
    });

    render(<AdSlot position="player_top" />);

    await waitFor(() => {
      expect(screen.getByTestId("ad-slot-player_top")).toHaveClass("md:hidden");
    });
  });
});
