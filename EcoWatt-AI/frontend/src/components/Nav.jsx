export default function Nav({
  region,
  onRegionChange,
  open,
  onToggle,
  onCloseMenu,
  current,
}) {
  return (
    <header className={open ? "nav open" : "nav"}>
      <div className="nav-inner">
        <a className="wordmark" href="#forecast" onClick={onCloseMenu}>
          <span className="mark" aria-hidden="true" />
          EcoWatt AI
        </a>

        <div className="nav-panel" id="mobile-nav">
          <nav className="nav-links" aria-label="Primary">
            <a href="#forecast" onClick={onCloseMenu} aria-current={current === "forecast" || undefined}>
              Energy Forecast
            </a>
            <a href="#planner" onClick={onCloseMenu} aria-current={current === "planner" || undefined}>
              Smart Planner
            </a>
            <a href="#results" onClick={onCloseMenu} aria-current={current === "results" || undefined}>
              Recommended Schedule
            </a>
          </nav>

          <div className="nav-right">
            <label className="region-label">
              <span className="visually-hidden">Region</span>
              <select
                className="region-select"
                value={region}
                onChange={(event) => onRegionChange(event.target.value)}
                aria-label="Forecast region"
              >
                <option value="gb">Great Britain</option>
                <option value="london">London</option>
              </select>
            </label>
          </div>
        </div>

        <button
          type="button"
          className="menu-toggle"
          aria-expanded={open}
          aria-controls="mobile-nav"
          onClick={onToggle}
        >
          Menu
        </button>
      </div>
    </header>
  );
}
