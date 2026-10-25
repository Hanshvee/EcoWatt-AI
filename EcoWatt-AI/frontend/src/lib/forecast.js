export function summarizeForecast(periods) {
  if (!periods?.length) {
    return { min: null, max: null, mean: null, cleanerThreshold: null };
  }
  const values = periods.map((period) => period.carbon_intensity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const sorted = [...values].sort((a, b) => a - b);
  const cleanerThreshold = sorted[Math.floor(sorted.length * 0.35)];
  return { min, max, mean, cleanerThreshold };
}

export function lowestIntensityPeriod(periods) {
  if (!periods?.length) {
    return null;
  }
  return periods.reduce((lowest, period) => {
    if (period.carbon_intensity < lowest.carbon_intensity) {
      return period;
    }
    if (
      period.carbon_intensity === lowest.carbon_intensity &&
      new Date(period.start_time) < new Date(lowest.start_time)
    ) {
      return period;
    }
    return lowest;
  });
}

export function chartPoints(periods) {
  const lowest = lowestIntensityPeriod(periods);
  return (periods || []).map((period) => ({
    time: period.start_time,
    intensity: period.carbon_intensity,
    end: period.end_time,
    isLowest: Boolean(lowest && period.start_time === lowest.start_time),
  }));
}

export function isCleanerPeriod(intensity, threshold) {
  return threshold != null && intensity <= threshold;
}
