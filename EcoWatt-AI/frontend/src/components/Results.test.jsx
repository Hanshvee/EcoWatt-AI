import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Results from "./Results.jsx";
import { formatBrowserTimeRange, formatGrams } from "../lib/time.js";

const start = "2026-10-25T19:00:00+00:00";
const finish = "2026-10-25T20:30:00+00:00";
const window = formatBrowserTimeRange(start, finish);

const single = {
  kind: "single",
  appliances: [
    {
      id: "single",
      name: "Dishwasher",
      start,
      finish,
      emissions: 55.1,
    },
  ],
  totalEmissions: 55.1,
  baseline: { available: true, total: 70.9, difference: 15.8, percent: 22.28490832157969 },
  solverStatus: null,
};

const multi = {
  kind: "multiple",
  appliances: [
    { id: "a", name: "Dishwasher", start, finish, emissions: 46.8 },
    {
      id: "b",
      name: "Dryer",
      start: "2026-10-25T20:30:00+00:00",
      finish: "2026-10-25T22:00:00+00:00",
      emissions: 73.2,
    },
  ],
  totalEmissions: 120,
  baseline: { available: true, total: 160, difference: 40, percent: 25 },
  solverStatus: "OPTIMAL",
};

describe("results", () => {
  it("renders a simple single-appliance card from the API payload", () => {
    render(<Results status="success" error="" result={single} />);

    expect(screen.getByText("Dishwasher")).toBeTruthy();
    expect(screen.getByText(`Recommended: ${window.time}`)).toBeTruthy();
    expect(screen.getByText(`Estimated emissions: ${formatGrams(55.1)} g CO2`)).toBeTruthy();
    expect(screen.getByText("Total recommended modeled emissions")).toBeTruthy();
    expect(screen.queryByLabelText("Recommended appliance timeline")).toBeNull();
    expect(document.querySelector(".timeline, .lane-bar, .bar")).toBeNull();
    expect(screen.getByText(/not verified avoided emissions/i)).toBeTruthy();
  });

  it("renders multi-appliance cards without timeline bars", () => {
    render(<Results status="success" error="" result={multi} />);

    expect(screen.getByText("Dryer")).toBeTruthy();
    expect(screen.getByText(`Estimated emissions: ${formatGrams(46.8)} g CO2`)).toBeTruthy();
    expect(screen.getByText(`Estimated emissions: ${formatGrams(73.2)} g CO2`)).toBeTruthy();
    expect(screen.getByText("25.0% lower")).toBeTruthy();
    expect(screen.getByText("OPTIMAL — proven best for this model.")).toBeTruthy();
    expect(screen.queryByLabelText("Recommended appliance timeline")).toBeNull();
    expect(document.querySelector(".timeline, .lane-fill, .bar")).toBeNull();
  });
});
