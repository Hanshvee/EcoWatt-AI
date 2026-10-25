import { formatBrowserTimeRange, formatGrams } from "../lib/time.js";

export default function Results({ status, error, result }) {
  const multi = result?.kind === "multiple" || (result?.appliances?.length || 0) > 1;

  return (
    <section className="band" id="results" aria-labelledby="results-title">
      <div className="section-head">
        <h2 id="results-title">Recommended Schedule</h2>
      </div>

      {status === "idle" && (
        <p className="fine">Run the planner to see when EcoWatt recommends using your appliances.</p>
      )}
      {status === "loading" && <div className="skeleton skeleton-short" aria-label="Preparing schedule" />}
      {status === "failure" && (
        <div className="alert alert-error" role="alert">
          {error || "The schedule could not be created."}
        </div>
      )}
      {status === "success" && result && (
        <div className="panel">
          <div className={multi ? "schedule-cards" : "schedule-cards schedule-cards-single"}>
            {result.appliances.map((item) => {
              const window = formatBrowserTimeRange(item.start, item.finish);
              return (
                <article className="schedule-card" key={item.id}>
                  <h3>{item.name}</h3>
                  <p>Recommended: {window.time}</p>
                  <p className="fine">{window.date}</p>
                  <p>Estimated emissions: {formatGrams(item.emissions ?? result.totalEmissions)} g CO2</p>
                </article>
              );
            })}
          </div>

          <dl className="emission-list">
            <div>
              <dt>Total recommended modeled emissions</dt>
              <dd>{formatGrams(result.totalEmissions)} g CO2</dd>
            </div>
            <div>
              <dt>Earliest feasible start</dt>
              <dd>{result.baseline.available ? `${formatGrams(result.baseline.total)} g CO2` : "—"}</dd>
            </div>
            {result.baseline.available && result.baseline.percent != null && (
              <div>
                <dt>Modeled difference</dt>
                <dd>{Number(result.baseline.percent).toFixed(1)}% lower</dd>
              </div>
            )}
          </dl>
          {!result.baseline.available && (
            <p className="fine">{result.baseline.reason || "No earliest-start comparison is available for this request."}</p>
          )}
          <p className="compare-note">
            These are modeled electricity-emissions comparisons, not verified avoided emissions.
            Times are shown in your local timezone.
          </p>
          {result.solverStatus && (
            <p className="solver-line">
              {result.solverStatus === "OPTIMAL" && "OPTIMAL — proven best for this model."}
              {result.solverStatus === "FEASIBLE" && "FEASIBLE — a valid plan, not proven optimal."}
              {result.solverStatus !== "OPTIMAL" && result.solverStatus !== "FEASIBLE" && result.solverStatus}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
