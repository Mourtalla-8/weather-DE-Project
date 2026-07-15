#!/usr/bin/env python3
"""
Weather ETL - MinIO raw -> Python nettoyage / transformation / normalisation -> MinIO processed

Ce script :
- lit weatherHistory.csv depuis MinIO (bucket raw),
- nettoie / normalise les données,
- sauvegarde une version CLEAN dans ./data/processed et dans MinIO (bucket weather-processed),
- sauvegarde une version ENRICHED dans ./data/processed et dans MinIO (bucket weather-processed),
- renvoie aussi un fichier metadata JSON.

Prérequis:
    pip install pandas minio python-dotenv pyarrow
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error


# --------------------------------------------------------------------
# Paths / environnement
# --------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

ENV_PATH = PROJECT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    # fallback: try current working directory .env
    load_dotenv()

DATA_DIR = PROJECT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------
# MinIO / S3-like settings from .env
# --------------------------------------------------------------------
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "groupea_de")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "ForceN-GroupeA-MinIO")
MINIO_RAW_BUCKET = os.getenv("MINIO_RAW_BUCKET", "weather-lake")
MINIO_RAW_PATH = os.getenv("MINIO_RAW_PATH", "raw/weatherHistory.csv")

# CLEAN version (bucket dédié aux données nettoyées)
MINIO_PROCESSED_BUCKET = os.getenv("MINIO_PROCESSED_BUCKET", "weather-processed")
MINIO_PROCESSED_PATH = os.getenv("MINIO_PROCESSED_PATH", "weather_processed.csv")

# ENRICHED version
MINIO_ENRICHED_BUCKET = os.getenv("MINIO_ENRICHED_BUCKET", "weather-processed")
MINIO_ENRICHED_PATH = os.getenv("MINIO_ENRICHED_PATH", "weather_processed_enriched.csv")

# Metadata
MINIO_METADATA_BUCKET = os.getenv("MINIO_METADATA_BUCKET", MINIO_PROCESSED_BUCKET)
MINIO_METADATA_PATH = os.getenv("MINIO_METADATA_PATH", "weatherHistory_clean_metadata.json")

# Local fallback (run without MinIO access)
RAW_LOCAL_FALLBACK = DATA_DIR / "minio" / MINIO_RAW_BUCKET / MINIO_RAW_PATH

# MinIO client
MINIO_HOST = MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
MINIO_SECURE = MINIO_ENDPOINT.startswith("https://")

minio_client = Minio(
    MINIO_HOST,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def ensure_bucket(bucket_name: str) -> None:
    """Create the bucket if it doesn't exist."""
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
    except S3Error as err:
        raise RuntimeError(
            f"Impossible de vérifier/créer le bucket '{bucket_name}': {err}"
        ) from err


def load_raw_dataframe() -> pd.DataFrame:
    """Load the raw CSV from MinIO first, fallback to local file if needed."""
    try:
        response = minio_client.get_object(MINIO_RAW_BUCKET, MINIO_RAW_PATH)
        try:
            df = pd.read_csv(response)
        finally:
            response.close()
            response.release_conn()
        return df
    except Exception as err:
        print(f"[INFO] Lecture MinIO impossible, fallback local: {err}")
        if not RAW_LOCAL_FALLBACK.exists():
            raise FileNotFoundError(
                f"Fichier introuvable: {RAW_LOCAL_FALLBACK}"
            ) from err
        return pd.read_csv(RAW_LOCAL_FALLBACK)


def snake_case(name: str) -> str:
    name = name.strip()
    name = name.replace("(", "").replace(")", "")
    name = name.replace("/", "_per_")
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_").lower()


def clean_weather_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean, normalize and standardize the weather dataset.
    This version does NOT add the derived time columns.
    """
    cleaned = df.copy()

    # Normalize column names
    cleaned.columns = [snake_case(c) for c in cleaned.columns]

    # Date / time parsing and rename
    if "formatted_date" not in cleaned.columns:
        raise KeyError(
            "La colonne 'Formatted Date' / 'formatted_date' est absente du dataset."
        )

    cleaned = cleaned.rename(columns={"formatted_date": "date_time"})
    cleaned["date_time"] = pd.to_datetime(cleaned["date_time"], errors="coerce", utc=True)
    cleaned = cleaned.dropna(subset=["date_time"]).copy()
    cleaned = cleaned.sort_values("date_time")
    cleaned = cleaned.drop_duplicates()

    # Text cleanup
    for col in ["summary", "precip_type", "daily_summary"]:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].astype("string").str.strip()

    # Normalize precip_type:
    # - NaN -> unknown
    # - lowercase for consistency
    if "precip_type" in cleaned.columns:
        cleaned["precip_type"] = (
            cleaned["precip_type"]
            .astype("string")
            .str.lower()
            .fillna("unknown")
        )

    # Drop constant / low-value column in this dataset
    if "loud_cover" in cleaned.columns:
        cleaned = cleaned.drop(columns=["loud_cover"])

    # Numeric conversion
    numeric_cols = [
        "temperature_c",
        "apparent_temperature_c",
        "humidity",
        "wind_speed_km_h",
        "wind_bearing_degrees",
        "visibility_km",
        "pressure_millibars",
    ]
    for col in numeric_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    # Pressure <= 0 is invalid and must be treated as missing
    if "pressure_millibars" in cleaned.columns:
        cleaned.loc[cleaned["pressure_millibars"] <= 0, "pressure_millibars"] = pd.NA

    # Keep only rows with the most important measurements
    important_cols = [c for c in ["temperature_c", "apparent_temperature_c", "humidity"] if c in cleaned.columns]
    if important_cols:
        cleaned = cleaned.dropna(subset=important_cols).copy()

    # Interpolate secondary measures
    cleaned = cleaned.set_index("date_time")
    for col in ["wind_speed_km_h", "wind_bearing_degrees", "visibility_km", "pressure_millibars"]:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].interpolate(method="time", limit_direction="both")
            cleaned[col] = cleaned[col].fillna(cleaned[col].median())
    cleaned = cleaned.reset_index()

    # More coherent dtypes
    for col in ["summary", "precip_type", "daily_summary"]:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].astype("string")

    return cleaned


def enrich_weather_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add time-based analytical columns to the CLEAN dataframe.
    """
    enriched = df.copy()

    enriched["date"] = enriched["date_time"].dt.date
    enriched["year"] = enriched["date_time"].dt.year.astype("int64")
    enriched["month"] = enriched["date_time"].dt.month.astype("int64")
    enriched["day"] = enriched["date_time"].dt.day.astype("int64")
    enriched["hour"] = enriched["date_time"].dt.hour.astype("int64")
    enriched["day_of_week"] = enriched["date_time"].dt.day_name().astype("string")

    return enriched


def save_outputs(df: pd.DataFrame, base_filename: str) -> dict[str, Path | None]:
    local_csv = PROCESSED_DIR / f"{base_filename}.csv"
    local_parquet = PROCESSED_DIR / f"{base_filename}.parquet"

    df.to_csv(local_csv, index=False)

    parquet_path: Path | None = None
    try:
        df.to_parquet(local_parquet, index=False)
        parquet_path = local_parquet
    except Exception as err:
        print(f"[INFO] Export Parquet ignoré pour {base_filename}: {err}")

    return {
        "csv": local_csv,
        "parquet": parquet_path,
    }


def write_metadata(metadata: dict, file_name: str = "weatherHistory_clean_metadata.json") -> Path:
    metadata_path = PROCESSED_DIR / file_name
    metadata_path.write_text(pd.Series(metadata).to_json(indent=2), encoding="utf-8")
    return metadata_path


def upload_to_minio(local_file: Path, bucket: str, key: str, content_type: str | None = None) -> None:
    minio_client.fput_object(
        bucket_name=bucket,
        object_name=key,
        file_path=str(local_file),
        content_type=content_type,
    )


# --------------------------------------------------------------------
# Main ETL
# --------------------------------------------------------------------

def main() -> None:
    print("=== Weather ETL ===")
    print("Project dir           :", PROJECT_DIR)
    print("Data dir              :", DATA_DIR)
    print("Processed dir         :", PROCESSED_DIR)
    print("MinIO endpoint        :", MINIO_ENDPOINT)
    print("RAW bucket / object   :", f"{MINIO_RAW_BUCKET}/{MINIO_RAW_PATH}")
    print("CLEAN bucket / object :", f"{MINIO_PROCESSED_BUCKET}/{MINIO_PROCESSED_PATH}")
    print("ENR bucket / object   :", f"{MINIO_ENRICHED_BUCKET}/{MINIO_ENRICHED_PATH}")

    ensure_bucket(MINIO_RAW_BUCKET)
    ensure_bucket(MINIO_PROCESSED_BUCKET)
    ensure_bucket(MINIO_ENRICHED_BUCKET)
    ensure_bucket(MINIO_METADATA_BUCKET)

    # Load
    df_raw = load_raw_dataframe()
    print("Shape brut :", df_raw.shape)

    # Clean
    df_clean = clean_weather_frame(df_raw)
    print("Shape clean :", df_clean.shape)

    # Enrich
    df_enriched = enrich_weather_frame(df_clean)
    print("Shape enrichi :", df_enriched.shape)

    # Report
    quality_report = pd.DataFrame({
        "metric": [
            "rows_raw",
            "rows_clean",
            "rows_enriched",
            "missing_precip_type_raw",
            "missing_precip_type_clean",
            "missing_precip_type_enriched",
            "invalid_pressure_raw",
            "invalid_pressure_clean",
        ],
        "value": [
            len(df_raw),
            len(df_clean),
            len(df_enriched),
            int(df_raw["Precip Type"].isna().sum()) if "Precip Type" in df_raw.columns else None,
            int(df_clean["precip_type"].isna().sum()) if "precip_type" in df_clean.columns else None,
            int(df_enriched["precip_type"].isna().sum()) if "precip_type" in df_enriched.columns else None,
            int((pd.to_numeric(df_raw["Pressure (millibars)"], errors="coerce") <= 0).sum()) if "Pressure (millibars)" in df_raw.columns else None,
            int(df_clean["pressure_millibars"].isna().sum()) if "pressure_millibars" in df_clean.columns else None,
        ]
    })
    print("\n=== Quality report ===")
    print(quality_report.to_string(index=False))

    # Save locally
    clean_outputs = save_outputs(df_clean, "weather_processed")
    enriched_outputs = save_outputs(df_enriched, "weather_processed_enriched")

    metadata = {
        "source_bucket": MINIO_RAW_BUCKET,
        "source_key": MINIO_RAW_PATH,
        "clean_rows": int(len(df_clean)),
        "enriched_rows": int(len(df_enriched)),
        "clean_columns": list(df_clean.columns),
        "enriched_columns": list(df_enriched.columns),
        "clean_csv_path": str(clean_outputs["csv"]),
        "enriched_csv_path": str(enriched_outputs["csv"]),
        "clean_parquet_path": str(clean_outputs["parquet"]) if clean_outputs["parquet"] else None,
        "enriched_parquet_path": str(enriched_outputs["parquet"]) if enriched_outputs["parquet"] else None,
    }
    metadata_path = write_metadata(metadata)

    print("\n=== Local outputs ===")
    print("Clean CSV local    :", clean_outputs["csv"])
    print("Clean Parquet local:", clean_outputs["parquet"])
    print("Enriched CSV local :", enriched_outputs["csv"])
    print("Enriched Parquet   :", enriched_outputs["parquet"])
    print("Metadata           :", metadata_path)

    # Upload CLEAN to MinIO
    upload_to_minio(
        clean_outputs["csv"],
        MINIO_PROCESSED_BUCKET,
        MINIO_PROCESSED_PATH,
        content_type="text/csv",
    )
    if clean_outputs["parquet"] is not None and clean_outputs["parquet"].exists():
        clean_parquet_object = MINIO_PROCESSED_PATH.rsplit(".", 1)[0] + ".parquet"
        upload_to_minio(
            clean_outputs["parquet"],
            MINIO_PROCESSED_BUCKET,
            clean_parquet_object,
            content_type="application/octet-stream",
        )

    # Upload ENRICHED to MinIO
    upload_to_minio(
        enriched_outputs["csv"],
        MINIO_ENRICHED_BUCKET,
        MINIO_ENRICHED_PATH,
        content_type="text/csv",
    )
    if enriched_outputs["parquet"] is not None and enriched_outputs["parquet"].exists():
        enriched_parquet_object = MINIO_ENRICHED_PATH.rsplit(".", 1)[0] + ".parquet"
        upload_to_minio(
            enriched_outputs["parquet"],
            MINIO_ENRICHED_BUCKET,
            enriched_parquet_object,
            content_type="application/octet-stream",
        )

    # Upload metadata
    upload_to_minio(
        metadata_path,
        MINIO_METADATA_BUCKET,
        MINIO_METADATA_PATH,
        content_type="application/json",
    )

    print("\nUpload terminé vers MinIO.")
    print(f"- {MINIO_PROCESSED_BUCKET}/{MINIO_PROCESSED_PATH}")
    print(f"- {MINIO_ENRICHED_BUCKET}/{MINIO_ENRICHED_PATH}")
    print(f"- {MINIO_METADATA_BUCKET}/{MINIO_METADATA_PATH}")


if __name__ == "__main__":
    main()

