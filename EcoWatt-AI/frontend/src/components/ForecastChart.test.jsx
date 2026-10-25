import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChartTooltip } from "./ForecastChart.jsx";
import { formatUkTooltip } from "../lib/time.js";

describe("forecast tooltip", () => {
  it("shows the NESO period date, start, end, timezone, intensity, and source", () => {
    const start = "2026-10-25T18:00:00+00:00";
    const end = "2026-10-25T18:30:00+00:00";
    const stamp = formatUkTooltip(start, end);
    render(
      <ChartTooltip
        active
        source="National Energy System Operator Carbon Intensity API"
        payload={[{ payload: { time: start, end, intensity: 52 } }]}
      />,
    );

    expect(screen.getByText(stamp.date)).toBeTruthy();
    expect(screen.getByText(`${stamp.start} – ${stamp.end}`)).toBeTruthy();
    expect(screen.getByText(stamp.zone)).toBeTruthy();
    expect(screen.getByText("52 gCO2/kWh")).toBeTruthy();
    expect(screen.getByText("National Energy System Operator Carbon Intensity API")).toBeTruthy();
  });
});
