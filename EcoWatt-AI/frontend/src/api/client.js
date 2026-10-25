const configuredBase = String(import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

// Dev uses same-origin /api so the browser never hits CORS. Vite proxies to the backend.
export const API_BASE_URL = import.meta.env.DEV ? "" : configuredBase || "http://127.0.0.1:8010";

export { configuredBase as CONFIGURED_API_BASE_URL };

export function parseApiError(payload, status) {
  const detail = payload?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (detail && typeof detail === "object" && !Array.isArray(detail) && detail.message) {
    return detail.message;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item.msg || item.message)
      .filter(Boolean)
      .join(" ");
  }
  return `Request failed with status ${status}.`;
}

export function networkErrorMessage(error) {
  const message = error?.message || "";
  if (error?.name === "AbortError") {
    return message;
  }
  if (error?.name === "TypeError" || /failed to fetch/i.test(message)) {
    return "Could not reach the EcoWatt AI service. Confirm the backend is running on port 8010.";
  }
  return message || "The request failed.";
}

export function apiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

async function request(path, options = {}) {
  try {
    const response = await fetch(apiUrl(path), {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });

    const text = await response.text();
    let payload = null;
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = null;
      }
    }

    if (!response.ok) {
      throw new Error(parseApiError(payload, response.status));
    }
    return payload;
  } catch (error) {
    if (error?.name === "AbortError") {
      throw error;
    }
    if (error instanceof Error && !/failed to fetch/i.test(error.message) && error.name !== "TypeError") {
      throw error;
    }
    throw new Error(networkErrorMessage(error));
  }
}

export async function fetchHealth(options = {}) {
  return request("/api/health", options);
}

export async function fetchCarbonForecast(region, options = {}) {
  const params = new URLSearchParams({ region });
  return request(`/api/carbon-forecast?${params.toString()}`, options);
}

export async function createSchedule(body, options = {}) {
  return request("/api/schedule", {
    ...options,
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function createMultiSchedule(body, options = {}) {
  return request("/api/schedule/multiple", {
    ...options,
    method: "POST",
    body: JSON.stringify(body),
  });
}
