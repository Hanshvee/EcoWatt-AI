import { describe, expect, it } from "vitest";
import { validatePlanner } from "./validation.js";

const appliance = {
  name: "Dishwasher",
  durationMinutes: 90,
  energyKwh: 1.2,
  earliestLocal: "2026-10-25T18:00",
  latestLocal: "2026-10-26T08:00",
};

describe("planner validation", () => {
  it("accepts a complete single appliance", () => {
    expect(validatePlanner({ appliances: [appliance], householdMaxPowerKw: 5 })).toEqual([]);
  });

  it("rejects empty numeric fields after the user clears them", () => {
    expect(
      validatePlanner({
        appliances: [{ ...appliance, durationMinutes: "", energyKwh: "" }],
        householdMaxPowerKw: 5,
      }).join(" "),
    ).toMatch(/duration|energy/i);
  });

  it("rejects missing appliances and invalid energy", () => {
    expect(validatePlanner({ appliances: [], householdMaxPowerKw: 5 }).length).toBeGreaterThan(0);
    expect(
      validatePlanner({
        appliances: [{ ...appliance, energyKwh: 0 }],
        householdMaxPowerKw: 5,
      })[0],
    ).toMatch(/energy/i);
  });

  it("requires two appliances in multiple mode", () => {
    expect(
      validatePlanner({
        appliances: [appliance],
        householdMaxPowerKw: 5,
        mode: "multiple",
      }).join(" "),
    ).toMatch(/at least two appliances/i);
  });

  it("requires 30-minute durations and household power for multi plans", () => {
    const errors = validatePlanner({
      appliances: [
        appliance,
        { ...appliance, name: "Dryer", durationMinutes: 45, energyKwh: 2 },
      ],
      householdMaxPowerKw: 0,
    });
    expect(errors.join(" ")).toMatch(/30-minute/);
    expect(errors.join(" ")).toMatch(/household maximum power/i);
  });
});
