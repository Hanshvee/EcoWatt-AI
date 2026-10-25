import { describe, expect, it } from "vitest";
import {
  normalizeDecimal,
  normalizeInteger,
  sanitizeDecimalInput,
  sanitizeIntegerInput,
} from "./numeric.js";

describe("numeric input sanitizing", () => {
  it("replaces a duration instead of concatenating onto the previous value", () => {
    expect(sanitizeIntegerInput("90")).toBe("90");
    expect(sanitizeIntegerInput("")).toBe("");
    expect(sanitizeIntegerInput("1")).toBe("1");
  });

  it("strips unwanted leading zeros from integer durations", () => {
    expect(sanitizeIntegerInput("090")).toBe("90");
    expect(sanitizeIntegerInput("0")).toBe("0");
  });

  it("accepts decimal energy values and strips a leading zero before the whole number", () => {
    expect(sanitizeDecimalInput("1.4")).toBe("1.4");
    expect(sanitizeDecimalInput("01.4")).toBe("1.4");
    expect(sanitizeDecimalInput("0.8")).toBe("0.8");
    expect(sanitizeDecimalInput("1.")).toBe("1.");
    expect(sanitizeDecimalInput(".")).toBe(".");
  });

  it("allows a field to stay empty while editing", () => {
    expect(sanitizeIntegerInput("")).toBe("");
    expect(sanitizeDecimalInput("")).toBe("");
    expect(normalizeInteger("")).toBe("");
    expect(normalizeDecimal("")).toBe("");
    expect(normalizeDecimal(".")).toBe("");
  });

  it("normalizes on blur without inventing zeros", () => {
    expect(normalizeInteger("090")).toBe("90");
    expect(normalizeDecimal("01.40")).toBe("1.4");
    expect(normalizeDecimal("2.0")).toBe("2");
  });
});
