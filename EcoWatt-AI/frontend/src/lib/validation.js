import { durationFits, fromLocalInputValue } from "./time.js";

export function validatePlanner({ appliances, householdMaxPowerKw, mode }) {
  const errors = [];

  if (!appliances.length) {
    errors.push("Add at least one appliance to plan.");
    return errors;
  }
  if (appliances.length > 6) {
    errors.push("The planner supports up to six appliances.");
  }
  if (mode === "multiple" && appliances.length < 2) {
    errors.push("Select at least two appliances for a household schedule.");
  }

  const multi = mode === "multiple" || appliances.length >= 2;
  if (multi && !(Number(householdMaxPowerKw) > 0)) {
    errors.push("Enter a household maximum power greater than 0 kW.");
  }

  appliances.forEach((item, index) => {
    const label = item.name || `Appliance ${index + 1}`;
    const duration = Number(item.durationMinutes);
    const energy = Number(item.energyKwh);

    if (!(duration > 0)) {
      errors.push(`${label}: duration must be greater than 0 minutes.`);
    } else if (multi && duration % 30 !== 0) {
      errors.push(`${label}: multi-appliance plans need a 30-minute duration.`);
    }

    if (!(energy > 0)) {
      errors.push(`${label}: estimated energy must be greater than 0 kWh.`);
    }

    let start;
    let finish;
    try {
      start = fromLocalInputValue(item.earliestLocal);
      finish = fromLocalInputValue(item.latestLocal);
    } catch {
      errors.push(`${label}: enter valid earliest start and finish times.`);
      return;
    }

    if (finish <= start) {
      errors.push(`${label}: the finish deadline must be after the earliest start.`);
    } else if (duration > 0 && !durationFits(start, finish, duration)) {
      errors.push(`${label}: the chosen window is shorter than the duration.`);
    }
  });

  return errors;
}
