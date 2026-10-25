import { afterEach, describe, expect, it, vi } from "vitest";
import { API_BASE_URL, apiUrl, fetchCarbonForecast, networkErrorMessage, parseApiError } from "./client.js";

describe("API helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses same-origin /api paths in development", () => {
    expect(API_BASE_URL).toBe("");
    expect(apiUrl("/api/carbon-forecast?region=gb")).toBe("/api/carbon-forecast?region=gb");
  });

  it("reads structured FastAPI errors", () => {
    expect(parseApiError({ detail: { message: "Unsupported region" } }, 400)).toBe(
      "Unsupported region",
    );
    expect(parseApiError({ detail: [{ msg: "duration" }] }, 422)).toBe("duration");
  });

  it("maps browser network failures away from Failed to fetch", () => {
    expect(networkErrorMessage(new TypeError("Failed to fetch"))).toMatch(/port 8010/);
  });

  it("requests the carbon forecast for the selected region", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ periods: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchCarbonForecast("london");
    expect(fetchMock).toHaveBeenCalled();
    expect(String(fetchMock.mock.calls[0][0])).toBe("/api/carbon-forecast?region=london");
  });

  it("throws when the forecast request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      text: async () => JSON.stringify({ detail: { message: "Could not reach the Carbon Intensity API." } }),
    }));

    await expect(fetchCarbonForecast("gb")).rejects.toThrow(/Could not reach/);
  });
});
