import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Timeline from "./Timeline.jsx";

describe("timeline", () => {
  it("renders recommended appliance windows", () => {
    render(
      <Timeline
        appliances={[
          {
            id: "a",
            name: "Dishwasher",
            start: "2026-10-25T23:00:00+00:00",
            finish: "2026-10-26T00:30:00+00:00",
            color: "#6E8CFF",
          },
        ]}
      />,
    );

    expect(screen.getByText("Dishwasher")).toBeTruthy();
    expect(screen.getByLabelText("Recommended appliance timeline")).toBeTruthy();
  });
});
