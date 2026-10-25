import { applianceMeta } from "./appliances.js";

export function normalizeScheduleResult(payload, kind) {
  if (!payload) {
    return null;
  }

  if (kind === "single") {
    const baselineTotal = payload.baseline?.estimated_emissions_gco2;
    const optimized = payload.estimated_emissions_gco2;
    const difference = payload.estimated_emissions_difference_gco2;
    const percent =
      baselineTotal > 0 ? (difference / baselineTotal) * 100 : null;

    return {
      kind,
      region: payload.region,
      solverStatus: null,
      provenOptimal: null,
      householdMaxPowerKw: null,
      appliances: [
        {
          id: "single",
          name: payload.appliance,
          type: payload.appliance_type,
          start: payload.recommended_start,
          finish: payload.recommended_finish,
          durationMinutes: payload.duration_minutes,
          energyKwh: payload.energy_kwh,
          emissions: optimized,
          color: applianceMeta(payload.appliance_type).color,
        },
      ],
      totalEmissions: optimized,
      baseline: payload.baseline
        ? {
            available: true,
            total: baselineTotal,
            difference,
            percent,
            appliances: [
              {
                id: "single-baseline",
                name: payload.appliance,
                start: payload.baseline.start,
                finish: payload.baseline.finish,
                emissions: baselineTotal,
              },
            ],
            reason: null,
          }
        : { available: false, reason: "No baseline was returned.", total: null },
      assumptions: payload.assumptions || [],
      disclaimer: payload.disclaimer,
      dataSource: payload.data_source,
    };
  }

  const baseline = payload.baseline || {};
  return {
    kind,
    region: payload.region,
    solverStatus: payload.solver_status,
    provenOptimal: payload.solver?.proven_optimal ?? payload.solver_status === "OPTIMAL",
    householdMaxPowerKw: payload.household_max_power_kw,
    appliances: (payload.appliances || []).map((item) => ({
      id: item.id,
      name: item.appliance,
      type: item.appliance_type,
      start: item.start,
      finish: item.finish,
      durationMinutes: item.duration_minutes,
      energyKwh: item.energy_kwh,
      powerKw: item.average_power_kw,
      emissions: item.estimated_emissions_gco2,
      color: applianceMeta(item.appliance_type).color,
    })),
    totalEmissions: payload.total_estimated_emissions_gco2,
    baseline: {
      available: Boolean(baseline.available),
      total: baseline.total_estimated_emissions_gco2 ?? null,
      difference: baseline.estimated_emissions_difference_gco2 ?? null,
      percent: baseline.estimated_emissions_difference_percent ?? null,
      reason: baseline.reason || null,
      appliances: (baseline.appliances || []).map((item) => ({
        id: item.id,
        name: item.appliance,
        start: item.start,
        finish: item.finish,
        emissions: item.estimated_emissions_gco2,
      })),
    },
    assumptions: payload.assumptions || [],
    disclaimer: payload.disclaimer,
    dataSource: payload.data_source,
  };
}
