import { useState } from "react";
import { APPLIANCES } from "../lib/appliances.js";
import { normalizeDecimal, normalizeInteger, sanitizeDecimalInput, sanitizeIntegerInput } from "../lib/numeric.js";

const ENERGY_HELP = "Not sure? We've added an example estimate. You can adjust it using your appliance's energy label.";

function ApplianceFields({ item, multi, onChangeAppliance }) {
  return (
    <div className="fields">
      <label className="field">
        <span>Duration, minutes</span>
        <input
          type="text"
          inputMode="numeric"
          autoComplete="off"
          value={item.durationMinutes}
          onChange={(event) => onChangeAppliance(item.key, {
            durationMinutes: sanitizeIntegerInput(event.target.value),
          })}
          onBlur={() => onChangeAppliance(item.key, {
            durationMinutes: normalizeInteger(item.durationMinutes),
          })}
        />
      </label>
      <label className="field">
        <span>Estimated electricity usage per cycle/session, kWh</span>
        <input
          type="text"
          inputMode="decimal"
          autoComplete="off"
          value={item.energyKwh}
          onChange={(event) => onChangeAppliance(item.key, {
            energyKwh: sanitizeDecimalInput(event.target.value),
          })}
          onBlur={() => onChangeAppliance(item.key, {
            energyKwh: normalizeDecimal(item.energyKwh),
          })}
        />
        <span className="field-help">{ENERGY_HELP}</span>
      </label>
      <label className="field">
        <span>Earliest start</span>
        <input
          type="datetime-local"
          step={multi ? 1800 : 60}
          value={item.earliestLocal}
          onChange={(event) => onChangeAppliance(item.key, { earliestLocal: event.target.value })}
        />
      </label>
      <label className="field">
        <span>Finish by</span>
        <input
          type="datetime-local"
          step={multi ? 1800 : 60}
          value={item.latestLocal}
          onChange={(event) => onChangeAppliance(item.key, { latestLocal: event.target.value })}
        />
      </label>
    </div>
  );
}

export default function Planner({
  mode,
  onMode,
  appliances,
  householdMaxPowerKw,
  onHouseholdPower,
  onSelectType,
  onChangeAppliance,
  onAdd,
  onRemove,
  onSubmit,
  submitting,
  errors,
}) {
  const multi = mode === "multiple";
  const [openKey, setOpenKey] = useState(appliances[0]?.key);

  return (
    <section className="band" id="planner" aria-labelledby="planner-title">
      <div className="section-head">
        <h2 id="planner-title">Smart Planner</h2>
        <div className="mode-switch" role="group" aria-label="Planner mode">
          <button type="button" aria-pressed={mode === "single"} onClick={() => onMode("single")}>
            Single
          </button>
          <button type="button" aria-pressed={mode === "multiple"} onClick={() => onMode("multiple")}>
            Multiple
          </button>
        </div>
      </div>

      <div className="panel">
        <div className="appliance-grid">
          {APPLIANCES.map((item) => {
            const selected = appliances.some((draft) => draft.type === item.type);
            return (
              <button
                key={item.type}
                type="button"
                className="card-button"
                aria-pressed={selected}
                onClick={() => onSelectType(item.type)}
              >
                <strong>{item.name}</strong>
                <span>{item.durationMinutes} min · {item.energyKwh} kWh </span>
              </button>
            );
          })}
        </div>

        {multi && (
          <label className="field household-field">
            <span>Household max power, kW</span>
            <input
              type="text"
              inputMode="decimal"
              autoComplete="off"
              value={householdMaxPowerKw}
              onChange={(event) => onHouseholdPower(sanitizeDecimalInput(event.target.value))}
              onBlur={() => onHouseholdPower(normalizeDecimal(householdMaxPowerKw))}
            />
          </label>
        )}

        {appliances.map((item) => {
          const expanded = !multi || openKey === item.key;
          return (
            <article className="draft-row" key={item.key}>
              {multi ? (
                <div className="toolbar draft-toolbar">
                  <button
                    type="button"
                    className="row-toggle"
                    aria-expanded={expanded}
                    onClick={() => setOpenKey(expanded ? "" : item.key)}
                  >
                    <strong>{item.name}</strong>
                    <span>{item.durationMinutes} min · {item.energyKwh} kWh</span>
                  </button>
                  <button type="button" className="button button-ghost" onClick={() => onRemove(item.key)}>
                    Remove
                  </button>
                </div>
              ) : (
                <h3>{item.name}</h3>
              )}
              {expanded && (
                <ApplianceFields item={item} multi={multi} onChangeAppliance={onChangeAppliance} />
              )}
            </article>
          );
        })}

        {multi && (
          <button type="button" className="button button-secondary" onClick={onAdd} disabled={appliances.length >= 6}>
            Add appliance
          </button>
        )}

        {errors.length > 0 && (
          <div className="alert alert-error" role="alert">
            {errors.map((error) => (
              <p key={error}>{error}</p>
            ))}
          </div>
        )}

        <button type="button" className="button button-primary button-block" onClick={onSubmit} disabled={submitting}>
          {submitting ? "Planning…" : "Find cleaner times"}
        </button>
      </div>
    </section>
  );
}
