# ⚡ EcoWatt AI

### Power Your Life. Protect Our Planet.

**AI-Powered Carbon-Aware Household Energy Scheduling**

**MarinaHacks 2026 | Social Good**

EcoWatt AI is an intelligent household energy scheduling platform designed to help people make more environmentally conscious electricity decisions.

By combining real electricity carbon-intensity forecasts, machine learning, and mathematical optimization, EcoWatt recommends lower-carbon operating windows for everyday household appliances.

Our mission is to **help households understand and potentially reduce their electricity-related carbon footprint without compromising their daily convenience.**

---

## 🌍 The Problem

Electricity does not have the same environmental impact throughout the day.

The electricity grid uses a changing mix of energy sources, including wind, solar, natural gas, and other forms of generation.

As this generation mix changes, the average carbon intensity of electricity also changes.

This means that consuming the same amount of electricity at two different times can result in different estimates of electricity-related carbon emissions.

However, most households do not have an easy way to understand these variations.

Appliances such as dishwashers, washing machines, dryers, and electric vehicle chargers are often operated without considering electricity carbon intensity.

**What if households could make more sustainable choices simply by changing when they use electricity?**

---

## 💡 Our Solution

EcoWatt AI makes carbon-aware electricity planning simple.

Users select an appliance, enter its estimated energy consumption, and choose when it can operate.

EcoWatt analyzes real electricity carbon-intensity forecasts and recommends an operating window with lower modeled emissions.

For households with multiple flexible appliances, EcoWatt optimizes the schedules together while respecting power limits and individual deadlines.

### How It Works

1. **Collect Data:** Retrieve real electricity carbon-intensity forecasts from the National Energy System Operator (NESO).
2. **Understand Preferences:** Collect appliance information, estimated energy usage, and scheduling constraints.
3. **Optimize Timing:** Identify feasible operating windows with the lowest modeled emissions.
4. **Recommend a Schedule:** Tell users when to operate their appliances.
5. **Explain the Impact:** Compare estimated emissions at the recommended time with an earliest-feasible schedule.

The goal is to transform complex energy information into understandable, actionable recommendations.

---

## 🌱 How EcoWatt AI Helps Reduce Carbon Footprints

EcoWatt encourages households to move flexible electricity consumption toward periods when the grid is forecast to have a lower average carbon intensity.

### 1. Identifying Cleaner Electricity Periods

The electricity generation mix changes throughout the day.

EcoWatt analyzes carbon-intensity forecasts to identify periods associated with lower estimated electricity-related emissions.

### 2. Recommending Better Appliance Times

Instead of requiring households to reduce appliance usage, EcoWatt recommends when flexible electrical appliances could operate.

For example, it may recommend running a dishwasher in the evening rather than earlier in the day when forecast carbon intensity is higher.

### 3. Optimizing Household Electricity Usage

EcoWatt coordinates multiple appliances while considering their energy consumption, operating duration, deadlines, and household power constraints.

This allows households to make coordinated energy decisions rather than scheduling each appliance independently.

### 4. Estimating Carbon Impact

EcoWatt calculates modeled electricity-related emissions using:

**Estimated emissions (gCO₂) = Electricity consumed (kWh) × Forecast carbon intensity (gCO₂/kWh)**

For an appliance operating across several forecast periods, the system calculates emissions for each interval and sums them.

#### Illustrative Example

| Scenario                 | Electricity Used | Average Carbon Intensity | Modeled Emissions |
| ------------------------ | ---------------: | -----------------------: | ----------------: |
| Earlier schedule         |          1.2 kWh |             150 gCO₂/kWh |          180 gCO₂ |
| Lower-intensity schedule |          1.2 kWh |              60 gCO₂/kWh |           72 gCO₂ |

**Modeled difference: 108 gCO₂, or 60% lower estimated emissions.**

Both schedules consume the same amount of electricity, but one has a lower forecast-based carbon-intensity estimate.

_These values are illustrative and not actual measurements from EcoWatt._

### 5. Encouraging Sustainable Habits

EcoWatt helps users:

- Understand how electricity carbon intensity changes.
- Identify lower-carbon opportunities for flexible appliance use.
- Make informed household energy decisions.
- Develop awareness of their electricity-related carbon footprint.
- Adopt more carbon-conscious electricity consumption habits.

### Important Environmental Distinction

EcoWatt's current comparisons use forecast **average electricity carbon intensity**, not marginal emissions.

Lower modeled emissions do not automatically prove that shifting appliance use reduces actual grid emissions.

EcoWatt therefore presents its results as forecast-based modeled comparisons rather than verified avoided emissions.

Its long-term aim is to support real-world carbon-footprint reductions as the system develops more accurate impact evaluation capabilities.

---

## ✨ Key Features

### 📈 Live Carbon Intensity Forecasts

- Integrates the official NESO Carbon Intensity API.
- Supports Great Britain and London.
- Retrieves available forecasts covering approximately 48 hours.
- Displays an interactive electricity carbon-intensity graph.
- Highlights the lowest forecast-intensity period.
- Shows dates, UK local times, and forecast values in gCO₂/kWh.

### 🏠 Single-Appliance Scheduling

Users can select supported appliances:

- Dishwasher
- Washing machine
- Dryer
- Electric vehicle charging

Users provide:

- Appliance duration
- Estimated electricity consumption
- Earliest start
- Finish deadline

EcoWatt evaluates feasible operating windows and recommends the one with the lowest modeled emissions.

### ⚡ Multi-Appliance Optimization

EcoWatt can optimize multiple appliances simultaneously using Google OR-Tools CP-SAT.

The optimizer considers:

- Individual operating windows
- Appliance durations
- Estimated energy requirements
- Continuous, non-interruptible appliance operation
- Household maximum power capacity
- Carbon-intensity forecasts

The objective is to minimize total forecast-based modeled emissions while respecting the scheduling constraints.

Multi-appliance scheduling operates on a 30-minute grid.

### 🧠 Machine Learning Forecasting

EcoWatt includes a trained XGBoost model for short-term national carbon-intensity forecasting.

The machine-learning pipeline covers:

- Historical electricity data acquisition
- Data cleaning
- Timestamp-aligned lag features
- Calendar and time-series feature engineering
- Chronological data splitting
- XGBoost model training
- Baseline comparisons
- Model evaluation

The model predicts Great Britain national average carbon intensity one 30-minute period ahead using available historical observations.

**The trained XGBoost pipeline is currently separate from the live appliance scheduler.** The scheduling APIs use NESO forecast data.

### 📊 Understandable Recommendations

EcoWatt presents:

- Recommended appliance operating times
- Individual appliance schedules
- Estimated modeled emissions
- An earliest-feasible scheduling baseline
- Modeled emissions differences
- Plain-language explanations
- Solver status for multi-appliance optimization

The website avoids overwhelming users with technical optimization details.

---

## 🛠️ Technology Stack

| Component         | Technology                    |
| ----------------- | ----------------------------- |
| Frontend          | React, Vite, JavaScript, CSS  |
| Backend           | Python, FastAPI, Pydantic     |
| Machine Learning  | XGBoost, pandas, scikit-learn |
| Optimization      | Google OR-Tools CP-SAT        |
| External API      | NESO Carbon Intensity API     |
| API Communication | REST, JSON, HTTPX             |
| Backend Testing   | Pytest                        |
| Frontend Testing  | Vitest                        |
| Version Control   | Git, GitHub                   |
| Planned Hosting   | Render                        |

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────────┐
                    │    EcoWatt AI Website   │
                    │       React + Vite      │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │      FastAPI Backend    │
                    └────────────┬────────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  │                             │
                  ▼                             ▼
       ┌─────────────────────┐       ┌─────────────────────┐
       │ NESO Carbon         │       │ Scheduling Engine   │
       │ Intensity API       │       │                     │
       └──────────┬──────────┘       └──────────┬──────────┘
                  │                             │
                  ▼                    ┌────────┴────────┐
       ┌─────────────────────┐         │                 │
       │ Forecast Data       │         ▼                 ▼
       │ Processing          │   Single Appliance   Multi-Appliance
       └─────────────────────┘   Scheduling         OR-Tools CP-SAT
                                          │              │
                                          └──────┬───────┘
                                                 ▼
                                  ┌─────────────────────────┐
                                  │ Recommended Schedules   │
                                  │ + Modeled CO2 Comparison│
                                  └─────────────────────────┘


                SEPARATE MACHINE LEARNING PIPELINE

                       NESO Historical Data
                                │
                                ▼
                       Data Preprocessing
                                │
                                ▼
                       Feature Engineering
                                │
                                ▼
                        XGBoost Training
                                │
                                ▼
                      One-Step Prediction
                         and Evaluation
```

---

## 🤖 Machine Learning Implementation

### Dataset

The XGBoost model was trained on approximately 180 days of historical Great Britain national carbon-intensity observations.

| Metric                          | Value |
| ------------------------------- | ----: |
| Historical observations         | 8,641 |
| Feature-engineered observations | 8,305 |
| Training observations           | 6,960 |
| Validation observations         |   672 |
| Test observations               |   673 |

### Feature Engineering

The forecasting model uses:

- Hour of day
- Day of week
- Month
- Cyclical calendar features
- Previous 30-minute intensity (`lag_1`)
- Previous 60-minute intensity (`lag_2`)
- Previous day's corresponding period (`lag_48`)
- Previous week's corresponding period (`lag_336`)

Lag features are matched by UTC timestamps to prevent incorrect alignment when historical observations are missing.

### Model Performance

| Forecasting Method      | Test MAE (gCO₂/kWh) | Test RMSE |
| ----------------------- | ------------------: | --------: |
| **XGBoost**             |            **4.21** |  **5.59** |
| Persistence baseline    |                5.30 |      7.23 |
| Seasonal-naive baseline |               38.89 |     49.92 |

The trained XGBoost model achieved a lower test error than the evaluated baseline methods.

**Note:** These results evaluate one-step-ahead forecasting using realized previous observations. They do not represent a 24-hour or 48-hour ahead forecast.

---

## ⚙️ Scheduling Optimization

EcoWatt minimizes forecast-weighted modeled emissions:

**Objective: Minimize Σ (appliance interval energy × interval carbon intensity)**

### Scheduling Constraints

- Each appliance must operate within its allowed time window.
- Appliance operation must be continuous.
- Duration requirements must be satisfied.
- Combined household appliance power must stay within the specified limit.
- All scheduled periods must have usable forecast coverage.
- Multi-appliance starts and durations must follow the 30-minute scheduling grid.

Google OR-Tools CP-SAT searches for feasible schedules satisfying these constraints.

When the solver returns `OPTIMAL`, it has proven optimality for the configured optimization model.

When it returns `FEASIBLE`, it has found a feasible solution but has not proven optimality.

---

## 🔌 REST API

| Method | Endpoint                             | Purpose                       |
| ------ | ------------------------------------ | ----------------------------- |
| GET    | `/api/health`                        | Backend health check          |
| GET    | `/api/carbon-forecast?region=gb`     | Great Britain forecast        |
| GET    | `/api/carbon-forecast?region=london` | London forecast               |
| POST   | `/api/schedule`                      | Single-appliance optimization |
| POST   | `/api/schedule/multiple`             | Multi-appliance optimization  |

### Example: Single-Appliance Scheduling

```json
{
  "region": "gb",
  "appliance": "dishwasher",
  "earliest_start": "2026-10-25T18:00:00+00:00",
  "latest_finish": "2026-10-26T08:00:00+00:00",
  "duration_minutes": 90,
  "energy_kwh": 1.2
}
```

The backend returns the recommended start and finish times, modeled emissions, baseline comparison, and relevant assumptions.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12
- Node.js and npm
- Git
- Internet connection for live NESO forecasts

### 1. Clone the Repository

```bash
git clone https://github.com/Hanshvee/EcoWatt-AI.git
cd EcoWatt-AI
```

The Git repository contains the application within an `EcoWatt-AI` subdirectory.

```bash
cd EcoWatt-AI
```

### 2. Start the FastAPI Backend

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Backend:

http://127.0.0.1:8010

Interactive API documentation:

http://127.0.0.1:8010/docs

### 3. Start the React Frontend

Open another terminal and navigate to the frontend:

```bash
cd EcoWatt-AI/EcoWatt-AI/frontend
```

Install dependencies:

```bash
npm install
```

Create `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8010
```

Start the frontend:

```bash
npm run dev
```

Open the local URL shown by Vite.

### 4. Run Tests

Backend:

```bash
python -m pytest
```

Frontend:

```bash
npm test
npm run build
```

---

## 🧪 Testing and Validation

EcoWatt includes automated coverage for:

- Carbon-intensity data retrieval
- NESO API error handling
- Forecast normalization
- Historical ML data processing
- Timestamp-aligned lag features
- Chronological model evaluation
- Single-appliance scheduling
- Multi-appliance optimization
- Household power constraints
- Infeasible requests
- Frontend form validation
- API response handling
- Recommendation rendering
- Timezone formatting

Both frontend and backend functionality were also manually tested against live NESO forecast data during development.

---

## 🎯 Social Good Impact

EcoWatt AI demonstrates how software engineering, machine learning, and mathematical optimization can help make sustainability more accessible.

### Who Can Benefit?

**Households:** Receive understandable guidance about when to operate flexible electrical appliances.

**EV Owners:** Explore lower-carbon charging opportunities within preferred charging windows.

**Environmentally Conscious Consumers:** Understand how electricity carbon intensity varies throughout the day.

**Communities:** Gain awareness of electricity-related carbon footprints and more flexible electricity-use habits.

### Long-Term Vision

Our vision is to make carbon-aware electricity planning a practical part of everyday life.

By making forecast information understandable and scheduling recommendations accessible, EcoWatt can encourage broader participation in carbon-conscious energy decisions.

---

## ⚠️ Current Limitations

- Live forecast coverage currently supports Great Britain and London.
- The platform depends on available NESO forecast data.
- The operating power of an appliance is modeled as uniform over its runtime.
- Multi-appliance scheduling uses 30-minute intervals.
- EcoWatt does not automatically control household appliances.

---

## 🔮 Future Enhancements

Potential future improvements include:

- Support for additional electricity grids and countries
- Custom appliance profiles
- Smart-home device integration
- Electricity price-aware optimization
- Notifications for recommended appliance operating times
- Natural-language scheduling assistant
- Longer-horizon machine-learning forecasting
- More advanced electricity-grid impact evaluation

These features represent future development opportunities rather than current functionality.

---

## 📚 Research Papers & References

EcoWatt AI is inspired by research in carbon-aware electricity optimization, household appliance scheduling, and sustainable energy management.

1. **On the Implications of Choosing Average versus Marginal Carbon Intensity Signals on Carbon-aware Optimizations (2024)**  
   Explores how different carbon-intensity metrics affect optimization decisions.  
   🔗 https://doi.org/10.1145/3632775.3661953

2. **Optimal Scheduling of Household Appliances for Demand Response (2014)**  
   Investigates optimizing household appliance schedules while considering user preferences and energy consumption.  
   🔗 https://doi.org/10.1016/j.epsr.2014.04.012

3. **A Survey of Efficient Demand-Side Management Techniques for the Residential Appliance Scheduling Problem in Smart Homes (2022)**  
   Reviews optimization techniques for smarter household electricity management.  
   🔗 https://doi.org/10.3390/en15082863

4. **Is Demand-Side Management Environmentally Beneficial? (2024)**  
   Examines whether shifting electricity consumption actually reduces greenhouse gas emissions.  
   🔗 https://doi.org/10.1016/j.jclepro.2023.140062

5. **Optimization-based Dynamic Life Cycle Assessment on Emission-based Demand Response Strategies in Danish Households (2026)**  
   Explores household electricity scheduling using time-dependent environmental impact assessment.  
   🔗 https://doi.org/10.1007/s40866-026-00328-x

_These papers provide scientific background and related research for EcoWatt AI. They are independent publications, not research authored by the EcoWatt team._

## 🏆 MarinaHacks 2026

**Hackathon:** MarinaHacks 2026

**Category:** Social Good

**Project:** EcoWatt AI

**Mission:** Make carbon-aware household energy decisions simple, accessible, and practical.

EcoWatt brings together live carbon-intensity forecasts, machine learning, and constrained optimization to demonstrate how technology can help households make more informed electricity-use decisions.

---

## 🔗 Repository

**GitHub:** https://github.com/Hanshvee/EcoWatt-AI

---

### ⚡ Power Your Life. Protect Our Planet.

_Smarter electricity decisions for a more sustainable future._
