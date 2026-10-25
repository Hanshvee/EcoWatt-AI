import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Forecast from "./Forecast.jsx";

describe("forecast", () => {
  it("uses the global region instead of a second selector", () => {
    render(<Forecast region="london" status="loading" forecast={null} error="" />);

    expect(screen.getByText(/London · gCO2\/kWh/)).toBeTruthy();
    expect(screen.queryByLabelText("Forecast region")).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("labels the lowest NESO period in UK local time", () => {
    render(
      <Forecast
        region="gb"
        status="success"
        forecast={{
          data_source: "National Energy System Operator Carbon Intensity API",
          periods: [
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
          ],
        }}
        error=""
      />,
    );

    expect(screen.getByText(/UK local time \(GMT\/BST\)/)).toBeTruthy();
    expect(screen.getByText(/Lowest forecast intensity: 41 gCO2\/kWh at/)).toBeTruthy();
  });

  it("surfaces NESO and API failures without fabricating periods", () => {
    render(
      <Forecast
        region="gb"
        status="failure"
        forecast={null}
        error="Could not reach the EcoWatt AI service. Confirm the backend is running on port 8010."
      />,
    );

    expect(screen.getByRole("alert").textContent).toMatch(/port 8010/);
  });
});
