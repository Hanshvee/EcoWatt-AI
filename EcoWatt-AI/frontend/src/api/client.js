const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}.`);
  }

  return response.json();
}

export { API_BASE_URL };
