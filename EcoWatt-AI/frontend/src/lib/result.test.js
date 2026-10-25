import { describe, expect, it } from "vitest";
import { normalizeScheduleResult } from "./result.js";

describe("schedule result mapping", () => {
  it("maps a single-appliance response", () => {
    const result = normalizeScheduleResult(
      {
        appliance: "Dishwasher",
        appliance_type: "dishwasher",
        region: "GB",
        recommended_start: "2026-10-25T23:00:00+00:00",
        recommended_finish: "2026-10-26T00:30:00+00:00",
        duration_minutes: 90,
        energy_kwh: 1.2,
        estimated_emissions_gco2: 96,
        baseline: {
          start: "2026-10-25T18:00:00+00:00",
          finish: "2026-10-25T19:30:00+00:00",
          estimated_emissions_gco2: 180,
        },
        estimated_emissions_difference_gco2: 84,
        assumptions: ["uniform"],
        disclaimer: "not verified",
        data_source: "NESO",
      },
      "single",
    );

    expect(result.appliances[0].start).toContain("2026-10-25");
    expect(result.baseline.available).toBe(true);
    expect(result.baseline.difference).toBe(84);
  });

  it("keeps a missing multi-appliance baseline unavailable", () => {
    const result = normalizeScheduleResult(
      {
        region: "GB",
        solver_status: "OPTIMAL",
        household_max_power_kw: 5,
        appliances: [],
        total_estimated_emissions_gco2: 12,
        baseline: { available: false, reason: "No earliest-start packing" },
        assumptions: [],
        disclaimer: "not verified",
      },
      "multiple",
    );

    expect(result.baseline.available).toBe(false);
    expect(result.baseline.difference).toBeNull();
    expect(result.solverStatus).toBe("OPTIMAL");
  });
});
