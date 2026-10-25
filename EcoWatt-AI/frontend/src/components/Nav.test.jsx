import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Nav from "./Nav.jsx";

const props = {
  region: "gb",
  onRegionChange: vi.fn(),
  open: false,
  onToggle: vi.fn(),
  onCloseMenu: vi.fn(),
  current: "forecast",
};

describe("navigation", () => {
  it("shows only forecast, planner, schedule, and one region control", () => {
    render(<Nav {...props} />);

    expect(screen.getByRole("link", { name: "Energy Forecast" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Smart Planner" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Recommended Schedule" })).toHaveAttribute("href", "#results");
    expect(screen.queryByRole("link", { name: "Overview" })).toBeNull();
    expect(screen.queryByText("Start Planning")).toBeNull();
    expect(screen.getAllByLabelText("Forecast region")).toHaveLength(1);
  });
});
