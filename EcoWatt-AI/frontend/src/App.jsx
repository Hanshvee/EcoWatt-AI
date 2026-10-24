import { useEffect, useState } from "react";
import { API_BASE_URL, fetchHealth } from "./api/client.js";

const STATUS = {
  loading: "loading",
  success: "success",
  failure: "failure",
};

function App() {
  const [status, setStatus] = useState(STATUS.loading);
  const [health, setHealth] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  async function checkConnection() {
    setStatus(STATUS.loading);
    setErrorMessage("");

    try {
      const result = await fetchHealth();
      setHealth(result);
      setStatus(STATUS.success);
    } catch (error) {
      setHealth(null);
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Unable to reach the EcoWatt AI backend.",
      );
      setStatus(STATUS.failure);
    }
  }

  useEffect(() => {
    checkConnection();
  }, []);

  return (
    <div className="page">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>

      <header className="hero">
        <p className="eyebrow">MarinaHacks 2026 · Social Goods</p>
        <h1>EcoWatt AI</h1>
        <p className="tagline">Power Your Life. Protect Our Planet.</p>
        <p className="intro">
          A simple, accessible way for households to start thinking about
          cleaner electricity timing. This starter screen confirms that the
          application is running and connected.
        </p>
      </header>

      <main id="main">
        <section className="card" aria-labelledby="connection-heading">
          <h2 id="connection-heading">Backend connection</h2>
          <p className="muted">Checking {API_BASE_URL}/api/health</p>

          {status === STATUS.loading && (
            <p className="status status-loading" role="status" aria-live="polite">
              Connecting to the EcoWatt AI backend…
            </p>
          )}

          {status === STATUS.success && (
            <div className="status status-success" role="status" aria-live="polite">
              <p>
                <strong>Connected.</strong> The backend is reachable and
                responding.
              </p>
              {health?.message && <p>{health.message}</p>}
              {health?.service && (
                <p className="muted">Service: {health.service}</p>
              )}
            </div>
          )}

          {status === STATUS.failure && (
            <div className="status status-failure" role="alert" aria-live="assertive">
              <p>
                <strong>Not connected.</strong> Start the backend, then try
                again.
              </p>
              {errorMessage && <p className="muted">{errorMessage}</p>}
            </div>
          )}

          <button type="button" className="button" onClick={checkConnection}>
            Check connection again
          </button>
        </section>

        <section className="card" aria-labelledby="about-heading">
          <h2 id="about-heading">What this starter includes</h2>
          <ul>
            <li>A React interface designed for clear reading and large tap targets.</li>
            <li>A FastAPI backend with a health check at /api/health.</li>
            <li>No estimated electricity use or carbon savings yet.</li>
          </ul>
        </section>
      </main>

      <footer>
        <p>EcoWatt AI · MarinaHacks 2026 · Social Goods</p>
      </footer>
    </div>
  );
}

export default App;
