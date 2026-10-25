from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models.schedule import ScheduleRequest, ScheduleResponse
from app.services.carbon_intensity import (
    CarbonIntensityError,
    CarbonIntensityResponseError,
    CarbonIntensityUnavailableError,
    CarbonIntensityService,
    UnsupportedRegionError,
)
from app.services.scheduler import ScheduleError, build_schedule

app = FastAPI(
    title="EcoWatt AI",
    description="Backend API for EcoWatt AI — MarinaHacks 2026 Social Goods.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

carbon_intensity_service = CarbonIntensityService()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ecowatt-ai",
        "message": "EcoWatt AI backend is running.",
    }


@app.get("/api/carbon-forecast")
def carbon_forecast(
    region: str = Query(
        default="gb",
        description="Forecast region. Use gb for national Great Britain or london for NESO region 13.",
    ),
) -> dict:
    try:
        return carbon_intensity_service.get_forecast(region)
    except UnsupportedRegionError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": exc.code, "message": exc.message},
        ) from exc
    except CarbonIntensityUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": exc.code,
                "message": exc.message,
                "data_source": "National Energy System Operator Carbon Intensity API",
            },
        ) from exc
    except CarbonIntensityResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": exc.code,
                "message": exc.message,
                "data_source": "National Energy System Operator Carbon Intensity API",
            },
        ) from exc
    except CarbonIntensityError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": exc.code, "message": exc.message},
        ) from exc


@app.post("/api/schedule")
def create_schedule(body: ScheduleRequest) -> ScheduleResponse:
    try:
        forecast = carbon_intensity_service.get_forecast(
            body.region,
            from_time=body.earliest_start,
        )
        return build_schedule(body, forecast)
    except ScheduleError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": exc.code, "message": exc.message},
        ) from exc
    except UnsupportedRegionError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": exc.code, "message": exc.message},
        ) from exc
    except CarbonIntensityUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": exc.code,
                "message": exc.message,
                "data_source": "National Energy System Operator Carbon Intensity API",
            },
        ) from exc
    except CarbonIntensityResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": exc.code,
                "message": exc.message,
                "data_source": "National Energy System Operator Carbon Intensity API",
            },
        ) from exc
    except CarbonIntensityError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": exc.code, "message": exc.message},
        ) from exc
