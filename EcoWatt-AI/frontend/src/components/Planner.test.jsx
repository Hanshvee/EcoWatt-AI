import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Planner from "./Planner.jsx";
import { validatePlanner } from "../lib/validation.js";

const dishwasher = {
  key: "dishwasher-1",
  type: "dishwasher",
  name: "Dishwasher",
  durationMinutes: "90",
  energyKwh: "1.2",
  earliestLocal: "2026-10-25T18:00",
  latestLocal: "2026-10-26T08:00",
};

function EditablePlanner({ initial = dishwasher }) {
  const [item, setItem] = useState(initial);
  return (
    <Planner
      mode="single"
      onMode={vi.fn()}
      appliances={[item]}
      householdMaxPowerKw="5"
      onHouseholdPower={vi.fn()}
      onSelectType={vi.fn()}
      onChangeAppliance={(_, patch) => setItem((current) => ({ ...current, ...patch }))}
      onAdd={vi.fn()}
      onRemove={vi.fn()}
      onSubmit={vi.fn()}
      submitting={false}
      errors={validatePlanner({ appliances: [item], householdMaxPowerKw: 5, mode: "single" })}
    />
  );
}

describe("planner", () => {
  it("keeps a single-appliance form, example energy copy, and the optimize action", () => {
    render(
      <Planner
        mode="single"
        onMode={vi.fn()}
        appliances={[dishwasher]}
        householdMaxPowerKw="5"
        onHouseholdPower={vi.fn()}
        onSelectType={vi.fn()}
        onChangeAppliance={vi.fn()}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
        onSubmit={vi.fn()}
        submitting={false}
        errors={[]}
      />,
    );

    expect(screen.getByRole("button", { name: "Single" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Find cleaner times" })).toBeTruthy();
    expect(screen.getByLabelText(/estimated electricity usage/i)).toHaveValue("1.2");
    expect(screen.getByText(/example estimate/i)).toBeTruthy();
  });

  it("lets the user replace, clear, and type duration and energy values", async () => {
    const user = userEvent.setup();
    render(<EditablePlanner />);

    const duration = screen.getByLabelText(/duration, minutes/i);
    const energy = screen.getByLabelText(/estimated electricity usage/i);

    await user.clear(duration);
    expect(duration).toHaveValue("");
    await user.type(duration, "90");
    expect(duration).toHaveValue("90");

    await user.clear(duration);
    await user.type(duration, "090");
    expect(duration).toHaveValue("90");

    await user.clear(energy);
    await user.type(energy, "01.4");
    expect(energy).toHaveValue("1.4");

    await user.clear(energy);
    expect(energy).toHaveValue("");
    expect(screen.getByRole("alert").textContent).toMatch(/energy/i);
  });

  it("exposes household power and compact rows in multiple mode", async () => {
    const user = userEvent.setup();
    const onAdd = vi.fn();
    const onMode = vi.fn();
    const onRemove = vi.fn();
    render(
      <Planner
        mode="multiple"
        onMode={onMode}
        appliances={[
          dishwasher,
          { ...dishwasher, key: "dryer-1", type: "dryer", name: "Dryer", energyKwh: "2" },
        ]}
        householdMaxPowerKw="5"
        onHouseholdPower={vi.fn()}
        onSelectType={vi.fn()}
        onChangeAppliance={vi.fn()}
        onAdd={onAdd}
        onRemove={onRemove}
        onSubmit={vi.fn()}
        submitting={false}
        errors={[]}
      />,
    );

    expect(screen.getByRole("button", { name: "Multiple" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText(/household max power/i)).toBeTruthy();
    const rowToggle = document.querySelector(".row-toggle");
    expect(rowToggle.querySelector("strong")?.textContent).toBe("Dishwasher");
    expect(rowToggle.querySelector("span")?.textContent).toMatch(/90 min · 1.2 kWh/);
    expect(rowToggle.querySelector("strong").tagName).toBe("STRONG");
    expect(rowToggle.querySelector("span").tagName).toBe("SPAN");
    await user.click(screen.getByRole("button", { name: "Add appliance" }));
    expect(onAdd).toHaveBeenCalled();
    await user.click(screen.getAllByRole("button", { name: "Remove" })[0]);
    expect(onRemove).toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Single" }));
    expect(onMode).toHaveBeenCalledWith("single");
  });
});
