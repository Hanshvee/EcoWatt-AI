import { afterEach, describe, expect, it, vi } from "vitest";
import {
  API_BASE_URL,
  PRODUCTION_API_BASE_URL,
  apiUrl,
  fetchCarbonForecast,
  networkErrorMessage,
  parseApiError,
  resolveApiBaseUrl,
} from "./client.js";

describe("API helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses same-origin /api paths in development", () => {
    expect(API_BASE_URL).toBe("");
    expect(apiUrl("/api/carbon-forecast?region=gb")).toBe("/api/carbon-forecast?region=gb");
  });

  it("uses the Render API when a production build has no configured base", () => {
    expect(resolveApiBaseUrl(false, "")).toBe(PRODUCTION_API_BASE_URL);
    expect(resolveApiBaseUrl(false, "https://ecowatt-ai-api.onrender.com")).toBe(
      "https://ecowatt-ai-api.onrender.com",
    );
  });

  it("reads structured FastAPI errors", () => {
    expect(parseApiError({ detail: { message: "Unsupported region" } }, 400)).toBe(
      "Unsupported region",
    );
    expect(parseApiError({ detail: [{ msg: "duration" }] }, 422)).toBe("duration");
  });

  it("maps browser network failures away from Failed to fetch", () => {
    expect(networkErrorMessage(new TypeError("Failed to fetch"), true)).toMatch(/port 8010/);
  });

  it("does not mention a local port when production cannot reach the API", () => {
    const message = networkErrorMessage(new TypeError("Failed to fetch"), false);
    expect(message).toMatch(/Could not reach the EcoWatt AI service/);
    expect(message).not.toMatch(/8010/);
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
