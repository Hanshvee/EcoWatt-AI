import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";
import { createMultiSchedule, createSchedule, fetchCarbonForecast } from "./api/client.js";

vi.mock("./api/client.js", () => ({
  API_BASE_URL: "",
  fetchCarbonForecast: vi.fn(),
  createSchedule: vi.fn(),
  createMultiSchedule: vi.fn(),
}));

const singlePayload = {
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
  assumptions: ["uniform power"],
  disclaimer: "Modeled estimates, not verified carbon savings.",
  data_source: "NESO Carbon Intensity API",
};

const multiPayload = {
  region: "GB",
  solver_status: "OPTIMAL",
  household_max_power_kw: 5,
  appliances: [
    {
      id: "dishwasher-1",
      appliance: "Dishwasher",
      appliance_type: "dishwasher",
      start: "2026-10-25T23:00:00+00:00",
      finish: "2026-10-26T00:30:00+00:00",
      duration_minutes: 90,
      energy_kwh: 1.2,
      estimated_emissions_gco2: 96,
    },
    {
      id: "dryer-1",
      appliance: "Dryer",
      appliance_type: "dryer",
      start: "2026-10-26T00:30:00+00:00",
      finish: "2026-10-26T02:00:00+00:00",
      duration_minutes: 90,
      energy_kwh: 2,
      estimated_emissions_gco2: 140,
    },
  ],
  total_estimated_emissions_gco2: 236,
  baseline: {
    available: true,
    total_estimated_emissions_gco2: 300,
    estimated_emissions_difference_gco2: 64,
    estimated_emissions_difference_percent: 21.3,
    appliances: [],
  },
  assumptions: ["30-minute slots"],
  disclaimer: "Modeled estimates, not verified carbon savings.",
};

beforeAll(() => {
  class IntersectionObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  vi.stubGlobal("IntersectionObserver", IntersectionObserverMock);
  Element.prototype.scrollIntoView = vi.fn();
});

beforeEach(() => {
  fetchCarbonForecast.mockResolvedValue({ region: "GB", periods: [] });
  createSchedule.mockResolvedValue(singlePayload);
  createMultiSchedule.mockResolvedValue(multiPayload);
});

describe("EcoWatt site flow", () => {
  it("keeps the demo sections and one region control", async () => {
    render(<App />);

    expect(screen.getByRole("link", { name: "Energy Forecast" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Smart Planner" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Recommended Schedule" })).toBeTruthy();
    expect(screen.queryByText("Start Planning")).toBeNull();
    expect(screen.queryByText("Plan My Energy")).toBeNull();
    expect(screen.getAllByLabelText("Forecast region")).toHaveLength(1);
    await waitFor(() => expect(fetchCarbonForecast).toHaveBeenCalledWith("gb", expect.anything()));
  });

  it("schedules one appliance with timezone-aware timestamps", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Find cleaner times" }));
    await waitFor(() => expect(createSchedule).toHaveBeenCalled());
    const body = createSchedule.mock.calls[0][0];
    expect(body.region).toBe("gb");
    expect(body.appliance).toBe("dishwasher");
    expect(body.earliest_start).toMatch(/Z$/);
    expect(body.latest_finish).toMatch(/Z$/);
    expect(await screen.findByText(/Recommended:/)).toBeTruthy();
    expect(screen.getAllByText("Dishwasher").length).toBeGreaterThan(0);
  });

  it("uses the multiple endpoint after switching mode", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Multiple" }));
    expect(screen.getByText("Household max power, kW")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Find cleaner times" }));
    await waitFor(() => expect(createMultiSchedule).toHaveBeenCalled());
    expect(createMultiSchedule.mock.calls[0][0]).toEqual(
      expect.objectContaining({ region: "gb", household_max_power_kw: 5 }),
    );
    expect(createMultiSchedule.mock.calls[0][0].appliances.length).toBeGreaterThanOrEqual(2);
    expect(await screen.findByText("OPTIMAL — proven best for this model.")).toBeTruthy();
  });

  it("reloads the forecast when the region changes", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.selectOptions(screen.getByLabelText("Forecast region"), "london");
    await waitFor(() => expect(fetchCarbonForecast).toHaveBeenCalledWith("london", expect.anything()));
    expect(screen.getByText(/London · gCO2\/kWh/)).toBeTruthy();
  });
});
