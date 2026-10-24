# EcoWatt AI — national intensity model (internal)

Predicts **Great Britain national average** electricity carbon intensity in **gCO2/kWh** from NESO estimated actuals. This is not a marginal-emissions model and is not wired into appliance scheduling.

## Data source

- Docs: https://carbon-intensity.github.io/api-definitions/
- Historical national actuals: `GET https://api.carbonintensity.org.uk/intensity/{from}/{to}`
- Official limit: 14 days per request. The downloader pages that window.
- Target field: `intensity.actual`. Missing actuals are dropped, never imputed.

## PowerShell commands

From the repo, using the existing backend virtual environment:

```powershell
cd D:\MarinaHack2026\EcoWatt-AI\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

cd D:\MarinaHack2026\EcoWatt-AI
.\backend\.venv\Scripts\python.exe -m ml.acquire
.\backend\.venv\Scripts\python.exe -m ml.train

cd D:\MarinaHack2026\EcoWatt-AI\backend
.\.venv\Scripts\python.exe -m pytest -q
```

If a NESO request fails, the scripts exit with an error. They do not write simulated training rows.

## Artifacts

| Path | Git |
| --- | --- |
| `data/raw/national_intensity_raw.jsonl` | ignored (raw download) |
| `data/processed/national_actuals.csv` | safe if you want a small cleaned table |
| `data/processed/national_features.csv` | optional; can be large |
| `models/xgb_national_intensity.json` | ignored (generated model) |
| `ml/artifacts/training_metadata.json` | safe (metrics and split sizes) |
| `docs/ML_TRAINING.md` | safe |

## Design notes

- Horizon: one half-hour period.
- Features at time `t`: calendar of `t` plus lags of **past** actuals only, joined on exact UTC timestamps (`t-30min`, `t-60min`, `t-24h`, `t-7d`).
- A missing historical timestamp leaves that lag empty; the row is then dropped. The previous kept row is never used as a stand-in.
- Splits are chronological: last 14 days test, prior 14 days validation, remainder train.
- Baselines: persistence (`lag_1`) and seasonal-naive (`lag_48`).
