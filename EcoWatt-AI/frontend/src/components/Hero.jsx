export default function Hero({ healthStatus, healthMessage }) {
  return (
    <section className="hero" id="overview" aria-labelledby="hero-title">
      <div>
        <p className="kicker">Power Your Life. Protect Our Planet.</p>
        <h1 id="hero-title">
          Smarter energy.
          <br />
          Lighter footprint.
        </h1>
        <p className="lede">Discover cleaner times to power your everyday life.</p>
        <div className="hero-actions">
          <a className="button button-primary" href="#planner">Plan My Energy</a>
          <a className="button button-secondary" href="#forecast">Explore Forecast</a>
        </div>
        <p className="connection" role="status">
          {healthStatus === "loading" && "Checking the EcoWatt AI service…"}
          {healthStatus === "success" && (healthMessage || "Connected to the EcoWatt AI service.")}
          {healthStatus === "failure" && "The planning service is unavailable. Forecasts and schedules will not load until it is running."}
        </p>
      </div>

      <div className="hero-visual" aria-hidden="true">
        <svg viewBox="0 0 640 480" role="presentation">
          <defs>
            <linearGradient id="wave" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#007AFF" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#16A085" stopOpacity="0.8" />
            </linearGradient>
          </defs>
          <path
            d="M20 300 C 90 220, 140 360, 220 280 S 360 180, 430 250 S 560 340, 620 230"
            fill="none"
            stroke="url(#wave)"
            strokeWidth="16"
            strokeLinecap="round"
          />
          <path
            d="M20 340 C 110 270, 170 390, 250 310 S 390 220, 470 290 S 560 360, 620 280"
            fill="none"
            stroke="rgba(255,255,255,0.7)"
            strokeWidth="8"
            strokeLinecap="round"
          />
          <circle cx="220" cy="280" r="14" fill="#fff" />
          <circle cx="430" cy="250" r="10" fill="#16A085" />
          <circle cx="250" cy="310" r="8" fill="#007AFF" />
        </svg>
        <div className="pulse" />
      </div>
    </section>
  );
}
