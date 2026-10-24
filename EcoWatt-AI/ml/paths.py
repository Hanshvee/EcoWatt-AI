from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"

RAW_JSONL = RAW_DIR / "national_intensity_raw.jsonl"
CLEANED_CSV = PROCESSED_DIR / "national_actuals.csv"
FEATURE_CSV = PROCESSED_DIR / "national_features.csv"
MODEL_PATH = MODELS_DIR / "xgb_national_intensity.json"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.json"
METADATA_PATH = ARTIFACTS_DIR / "training_metadata.json"

UNITS = "gCO2/kWh"
DATA_SOURCE = "National Energy System Operator Carbon Intensity API"
REGION = "GB"
TARGET_COLUMN = "actual_gco2_per_kwh"
API_BASE_URL = "https://api.carbonintensity.org.uk"
MAX_RANGE_DAYS = 14
