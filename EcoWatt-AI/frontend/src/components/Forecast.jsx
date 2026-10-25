import ForecastChart from "./ForecastChart.jsx";
import { chartPoints, lowestIntensityPeriod, summarizeForecast } from "../lib/forecast.js";
import { formatUkAxisTick } from "../lib/time.js";

const REGION_LABEL = { gb: "Great Britain", london: "London" };

export default function Forecast({ region, status, forecast, error }) {
  const periods = forecast?.periods || [];
  const points = chartPoints(periods);
  const summary = summarizeForecast(periods);
  const lowest = lowestIntensityPeriod(periods);
  const source = forecast?.data_source || "National Energy System Operator Carbon Intensity API";

  return (
    <section className="band" id="forecast" aria-labelledby="forecast-title">
      <div className="section-head">
        <h2 id="forecast-title">Energy Forecast</h2>
        <p className="region-chip">{REGION_LABEL[region] || region} · gCO2/kWh</p>
      </div>

      <div className="panel">
        {status === "loading" && <div className="skeleton" aria-label="Loading forecast" />}
        {status === "failure" && (
          <div className="alert alert-error" role="alert">
            {error || "The forecast is unavailable right now."}
          </div>
        )}
        {status === "success" && !periods.length && (
          <div className="alert alert-error" role="status">
            NESO did not return usable forecast periods for this region.
          </div>
        )}
        {status === "success" && periods.length > 0 && (
          <>
            <p className="chart-tz">UK local time (GMT/BST)</p>
            <ForecastChart points={points} source={source} />
            <p className="chart-summary">
              {summary.min}–{summary.max} gCO2/kWh over the next two days.
            </p>
            {lowest && (
              <p className="lowest-label">
                Lowest forecast intensity: {lowest.carbon_intensity} gCO2/kWh at {formatUkAxisTick(lowest.start_time)}.
              </p>
            )}
            <p className="fine">
              This is the lowest half-hour in the NESO forecast, not necessarily the best window for a longer appliance cycle.
            </p>
          </>
        )}
      </div>
    </section>
  );
}
