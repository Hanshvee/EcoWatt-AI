import { nextHalfHour, toLocalInputValue } from "./time.js";

export const APPLIANCES = [
  {
    type: "dishwasher",
    name: "Dishwasher",
    detail: "Evening cycles, about 90 minutes",
    durationMinutes: 90,
    energyKwh: 1.2,
    color: "#6E8CFF",
  },
  {
    type: "washing_machine",
    name: "Washing machine",
    detail: "Everyday laundry, about 60 minutes",
    durationMinutes: 60,
    energyKwh: 0.8,
    color: "#3DB8A4",
  },
  {
    type: "dryer",
    name: "Dryer",
    detail: "Tumble dry, about 90 minutes",
    durationMinutes: 90,
    energyKwh: 2,
    color: "#C49A6C",
  },
  {
    type: "ev_charging",
    name: "EV charging",
    detail: "A typical home charge session",
    durationMinutes: 180,
    energyKwh: 7,
    color: "#8A7CFF",
  },
];

export function applianceMeta(type) {
  return APPLIANCES.find((item) => item.type === type) || APPLIANCES[0];
}

export function createApplianceDraft(type, index = 1) {
  const meta = applianceMeta(type);
  const earliest = nextHalfHour();
  const latest = new Date(earliest.getTime() + 12 * 60 * 60 * 1000);
  return {
    key: `${type}-${Date.now()}-${index}`,
    type: meta.type,
    name: meta.name,
    durationMinutes: String(meta.durationMinutes),
    energyKwh: String(meta.energyKwh),
    earliestLocal: toLocalInputValue(earliest),
    latestLocal: toLocalInputValue(latest),
  };
}
