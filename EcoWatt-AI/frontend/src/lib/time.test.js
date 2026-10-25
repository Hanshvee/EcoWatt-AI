import { describe, expect, it } from "vitest";
import {
  durationFits,
  formatLocal,
  formatUkAxisTick,
  formatUkTooltip,
  parseIso,
  snapToHalfHourUtc,
  toIsoUtc,
  ukTimeZoneName,
} from "./time.js";

describe("time helpers", () => {
  it("parses ISO timestamps and keeps UTC in ISO form", () => {
    const iso = "2026-10-25T18:00:00+00:00";
    const date = parseIso(iso);
    expect(toIsoUtc(date)).toBe("2026-10-25T18:00:00.000Z");
  });

  it("formats timestamps in the local timezone", () => {
    const formatted = formatLocal("2026-10-25T18:00:00+00:00");
    expect(formatted).toMatch(/2026|Oct|25/);
  });

  it("snaps to a 30-minute UTC boundary", () => {
    const snapped = snapToHalfHourUtc(new Date("2026-10-25T18:14:00.000Z"));
    expect(snapped.getUTCMinutes()).toBe(0);
    expect(snapped.getUTCHours()).toBe(18);
  });

  it("formats forecast ticks in Europe/London with a date", () => {
    expect(formatUkAxisTick("2026-10-25T07:00:00+00:00")).toMatch(/Oct 25,/);
    expect(formatUkAxisTick("2026-10-26T00:00:00+00:00")).toMatch(/Oct 2[56],/);
  });

  it("converts UTC to Europe/London across the spring DST change", () => {
    expect(ukTimeZoneName("2026-03-29T00:30:00Z")).toBe("GMT");
    expect(formatUkAxisTick("2026-03-29T00:30:00Z")).toMatch(/12:30 AM|12:30 am/i);
    expect(ukTimeZoneName("2026-03-29T01:30:00Z")).toBe("BST");
    expect(formatUkAxisTick("2026-03-29T01:30:00Z")).toMatch(/2:30 AM|2:30 am/i);
  });

  it("converts UTC to Europe/London across the autumn DST change", () => {
    expect(ukTimeZoneName("2026-10-25T00:30:00Z")).toBe("BST");
    expect(formatUkAxisTick("2026-10-25T00:30:00Z")).toMatch(/1:30 AM|1:30 am/i);
    expect(ukTimeZoneName("2026-10-25T01:30:00Z")).toBe("GMT");
    expect(formatUkAxisTick("2026-10-25T01:30:00Z")).toMatch(/1:30 AM|1:30 am/i);
  });

  it("formats tooltip timestamps with date, range, and UK zone", () => {
    const tip = formatUkTooltip("2026-10-25T18:00:00+00:00", "2026-10-25T18:30:00+00:00");
    expect(tip.date).toMatch(/October 25/);
    expect(tip.start).toMatch(/6:00 PM|18:00/);
    expect(tip.end).toMatch(/6:30 PM|18:30/);
    expect(tip.zone).toMatch(/UK local time \(BST|GMT\)/);
  });

  it("checks whether a duration fits a window", () => {
    const start = new Date("2026-10-25T18:00:00.000Z");
    const finish = new Date("2026-10-25T19:00:00.000Z");
    expect(durationFits(start, finish, 60)).toBe(true);
    expect(durationFits(start, finish, 90)).toBe(false);
  });
});
