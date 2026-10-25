import { describe, expect, it } from "vitest";
import { chartPoints, lowestIntensityPeriod } from "./forecast.js";

const periods = [
  {
    start_time: "2026-10-25T18:00:00+00:00",
    end_time: "2026-10-25T18:30:00+00:00",
    carbon_intensity: 80,
  },
  {
    start_time: "2026-10-25T18:30:00+00:00",
    end_time: "2026-10-25T19:00:00+00:00",
    carbon_intensity: 41,
  },
  {
    start_time: "2026-10-26T07:00:00+00:00",
    end_time: "2026-10-26T07:30:00+00:00",
    carbon_intensity: 41,
  },
];

describe("forecast mapping", () => {
  it("uses NESO start_time and end_time instead of generated dates", () => {
    const points = chartPoints(periods);
    expect(points.map((point) => point.time)).toEqual(periods.map((period) => period.start_time));
    expect(points.map((point) => point.end)).toEqual(periods.map((period) => period.end_time));
    expect(points.map((point) => point.intensity)).toEqual(periods.map((period) => period.carbon_intensity));
  });

  it("selects the earliest lowest-intensity period from the API response", () => {
    const lowest = lowestIntensityPeriod(periods);
    expect(lowest.start_time).toBe("2026-10-25T18:30:00+00:00");
    expect(lowest.carbon_intensity).toBe(41);
    expect(chartPoints(periods).filter((point) => point.isLowest)).toHaveLength(1);
  });
});
