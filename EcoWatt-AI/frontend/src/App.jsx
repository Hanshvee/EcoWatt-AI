import { useEffect, useState } from "react";
import {
  createMultiSchedule,
  createSchedule,
  fetchCarbonForecast,
} from "./api/client.js";
import Forecast from "./components/Forecast.jsx";
import Nav from "./components/Nav.jsx";
import Planner from "./components/Planner.jsx";
import Results from "./components/Results.jsx";
import { APPLIANCES, createApplianceDraft } from "./lib/appliances.js";
import { normalizeScheduleResult } from "./lib/result.js";
import { fromLocalInputValue, snapToHalfHourUtc, toIsoUtc } from "./lib/time.js";
import { validatePlanner } from "./lib/validation.js";

function nextUnusedType(current) {
  return APPLIANCES.find((item) => !current.some((draft) => draft.type === item.type))?.type
    || current[0]?.type
    || "dishwasher";
}

export default function App() {
  const [region, setRegion] = useState("gb");
  const [menuOpen, setMenuOpen] = useState(false);
  const [forecastStatus, setForecastStatus] = useState("loading");
  const [forecast, setForecast] = useState(null);
  const [forecastError, setForecastError] = useState("");
  const [mode, setMode] = useState("single");
  const [appliances, setAppliances] = useState([createApplianceDraft("dishwasher")]);
  const [householdMaxPowerKw, setHouseholdMaxPowerKw] = useState("5");
  const [formErrors, setFormErrors] = useState([]);
  const [resultStatus, setResultStatus] = useState("idle");
  const [resultError, setResultError] = useState("");
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [currentSection, setCurrentSection] = useState("forecast");

  useEffect(() => {
    const controller = new AbortController();
    setForecastStatus("loading");
    setForecastError("");
    fetchCarbonForecast(region, { signal: controller.signal })
      .then((payload) => {
        setForecast(payload);
        setForecastStatus("success");
      })
      .catch((error) => {
        if (error.name === "AbortError") {
          return;
        }
        setForecast(null);
        setForecastStatus("failure");
        setForecastError(error.message);
      });
    return () => controller.abort();
  }, [region]);

  useEffect(() => {
    const ids = ["forecast", "planner", "results"];
    const elements = ids.map((id) => document.getElementById(id)).filter(Boolean);
    if (!elements.length) {
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target?.id) {
          setCurrentSection(visible.target.id);
        }
      },
      { rootMargin: "-18% 0px -55% 0px", threshold: [0.15, 0.35, 0.6] },
    );
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [resultStatus]);

  function setPlannerMode(next) {
    setMode(next);
    setFormErrors([]);
    if (next === "single") {
      setAppliances((current) => [current[0] || createApplianceDraft("dishwasher")]);
      return;
    }
    setAppliances((current) => {
      if (current.length >= 2) {
        return current;
      }
      const first = current[0] || createApplianceDraft("dishwasher");
      return [first, createApplianceDraft(nextUnusedType([first]), 2)];
    });
  }

  function updateAppliance(key, patch) {
    setAppliances((current) =>
      current.map((item) => (item.key === key ? { ...item, ...patch } : item)),
    );
  }

  function addAppliance() {
    if (mode !== "multiple") {
      return;
    }
    setAppliances((current) =>
      current.length >= 6 ? current : [...current, createApplianceDraft(nextUnusedType(current), current.length + 1)],
    );
  }

  function selectType(type) {
    if (mode === "single") {
      setAppliances([createApplianceDraft(type)]);
      return;
    }
    setAppliances((current) => {
      const existing = current.find((item) => item.type === type);
      if (existing) {
        return current.length <= 2 ? current : current.filter((item) => item.key !== existing.key);
      }
      if (current.length >= 6) {
        return current;
      }
      return [...current, createApplianceDraft(type, current.length + 1)];
    });
  }

  function removeAppliance(key) {
    setAppliances((current) => {
      if (mode === "multiple" && current.length <= 2) {
        return current;
      }
      const next = current.filter((item) => item.key !== key);
      return next.length ? next : [createApplianceDraft("dishwasher")];
    });
  }

  async function submitPlan() {
    const errors = validatePlanner({ appliances, householdMaxPowerKw, mode });
    setFormErrors(errors);
    if (errors.length) {
      return;
    }

    setSubmitting(true);
    setResultStatus("loading");
    setResultError("");
    setResult(null);

    try {
      if (mode === "single" || appliances.length === 1) {
        const item = appliances[0];
        const payload = await createSchedule({
          region,
          appliance: item.type,
          earliest_start: toIsoUtc(fromLocalInputValue(item.earliestLocal)),
          latest_finish: toIsoUtc(fromLocalInputValue(item.latestLocal)),
          duration_minutes: Number(item.durationMinutes),
          energy_kwh: Number(item.energyKwh),
        });
        setResult(normalizeScheduleResult(payload, "single"));
      } else {
        const payload = await createMultiSchedule({
          region,
          household_max_power_kw: Number(householdMaxPowerKw),
          appliances: appliances.map((item, index) => ({
            id: `${item.type}-${index + 1}`,
            appliance: item.type,
            earliest_start: toIsoUtc(snapToHalfHourUtc(fromLocalInputValue(item.earliestLocal))),
            latest_finish: toIsoUtc(snapToHalfHourUtc(fromLocalInputValue(item.latestLocal))),
            duration_minutes: Number(item.durationMinutes),
            energy_kwh: Number(item.energyKwh),
          })),
        });
        setResult(normalizeScheduleResult(payload, "multiple"));
      }
      setResultStatus("success");
      window.requestAnimationFrame(() => {
        document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (error) {
      setResultStatus("failure");
      setResultError(error.message || "The schedule request failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="app">
      <a className="skip-link" href="#forecast">Skip to content</a>
      <Nav
        region={region}
        onRegionChange={setRegion}
        open={menuOpen}
        onToggle={() => setMenuOpen((value) => !value)}
        onCloseMenu={() => setMenuOpen(false)}
        current={currentSection}
      />
      <main>
        <Forecast
          region={region}
          status={forecastStatus}
          forecast={forecast}
          error={forecastError}
        />
        <Planner
          mode={mode}
          onMode={setPlannerMode}
          appliances={appliances}
          householdMaxPowerKw={householdMaxPowerKw}
          onHouseholdPower={setHouseholdMaxPowerKw}
          onSelectType={selectType}
          onChangeAppliance={updateAppliance}
          onAdd={addAppliance}
          onRemove={removeAppliance}
          onSubmit={submitPlan}
          submitting={submitting}
          errors={formErrors}
        />
        <Results status={resultStatus} error={resultError} result={result} />
      </main>
    </div>
  );
}
