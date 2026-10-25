# EcoWatt AI — multi-appliance scheduling (internal)

`POST /api/schedule/multiple` packs 2–6 household appliances onto NESO 30-minute carbon-intensity forecasts with Google OR-Tools CP-SAT. Single-appliance `POST /api/schedule` is unchanged.

This is **not** verified avoided emissions. A `FEASIBLE` solver status is **not** a proven optimum.

## Model

- Decision: one start slot per appliance on the 30-minute grid.
- Each run is continuous and non-interruptible.
- Average power = `energy_kwh / duration_hours`.
- Capacity: in every occupied slot, Σ appliance power ≤ household max.
- Objective: minimize forecast-weighted modeled grams CO2.
- Integer scaling: power uses kW × 1000 (appliance ceil, household floor). Emissions use gCO2 × 1000.
- Tie-break: among equal modeled emissions, earlier start slots are preferred.
- Time limit: 10 seconds, seed 42, one search worker.

Forecasts come from the existing NESO client (`/intensity/{from}/fw48h` or London `regionid/13`). Missing half-hours are not invented.

## Baseline

Greedy earliest-start packing with the same capacity and deadlines. If that packing fails, `baseline.available` is false and no baseline emissions are reported.

## PowerShell

```powershell
cd D:\MarinaHack2026\EcoWatt-AI\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
$body = @{
  region = "gb"
  household_max_power_kw = 5
  appliances = @(
    @{
      id = "dishwasher-1"
      appliance = "dishwasher"
      earliest_start = "2026-10-25T18:00:00+00:00"
      latest_finish = "2026-10-26T08:00:00+00:00"
      duration_minutes = 90
      energy_kwh = 1.2
    },
    @{
      id = "washer-1"
      appliance = "washing_machine"
      earliest_start = "2026-10-25T18:00:00+00:00"
      latest_finish = "2026-10-26T08:00:00+00:00"
      duration_minutes = 60
      energy_kwh = 0.8
    }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/api/schedule/multiple `
  -ContentType "application/json" -Body $body
```

Use a window inside NESO’s ~48-hour forecast. Times must be timezone-aware and on the hour or half-hour. Durations must be multiples of 30 minutes.
