import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ScheduleFilterTabs from "../ScheduleFilterTabs";

describe("ScheduleFilterTabs", () => {
  it("renders the three Arabic date pills with the active pill selected", () => {
    render(<ScheduleFilterTabs activeTab="today" onTabChange={vi.fn()} />);

    expect(screen.getByRole("tablist")).toHaveAttribute("dir", "rtl");
    expect(screen.getByTestId("schedule-tab-yesterday")).toHaveTextContent("مباريات الأمس");
    expect(screen.getByTestId("schedule-tab-today")).toHaveTextContent("مباريات اليوم");
    expect(screen.getByTestId("schedule-tab-tomorrow")).toHaveTextContent("مباريات الغد");

    expect(screen.getByTestId("schedule-tab-today")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("schedule-tab-yesterday")).toHaveAttribute("aria-selected", "false");
  });

  it("emits the selected date key", () => {
    const onTabChange = vi.fn();
    render(<ScheduleFilterTabs activeTab="today" onTabChange={onTabChange} />);

    fireEvent.click(screen.getByTestId("schedule-tab-tomorrow"));
    expect(onTabChange).toHaveBeenCalledWith("tomorrow");

    fireEvent.click(screen.getByTestId("schedule-tab-yesterday"));
    expect(onTabChange).toHaveBeenCalledWith("yesterday");
  });
});
