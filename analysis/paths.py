"""Chemins et résolution des données ETL pour l'analyse."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
LOCAL_ENRICHED_CSV = PROCESSED_DIR / "weather_processed_enriched.csv"
LOCAL_CLEAN_CSV = PROCESSED_DIR / "weather_processed.csv"

OUTPUT_EDA = REPO_ROOT / "outputs" / "eda"
OUTPUT_ML = REPO_ROOT / "outputs" / "ml"

EXPECTED_ROW_COUNT = 96_429

MINIO_PROCESSED_BUCKET = os.getenv("MINIO_PROCESSED_BUCKET", "weather-processed")
MINIO_ENRICHED_PATH = os.getenv("MINIO_ENRICHED_PATH", "weather_processed_enriched.csv")


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value) if value else default


ENRICHED_CSV = _env_path("WEATHER_ENRICHED_CSV", LOCAL_ENRICHED_CSV)


def ensure_output_dirs() -> None:
    OUTPUT_EDA.mkdir(parents=True, exist_ok=True)
    OUTPUT_ML.mkdir(parents=True, exist_ok=True)


def _download_enriched_from_minio(target: Path) -> None:
    """Télécharge le CSV enrichi depuis MinIO (sortie ETL transform.py)."""
    from dotenv import load_dotenv
    from minio import Minio

    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "groupea_de")
    secret_key = os.getenv("MINIO_SECRET_KEY", "ForceN-GroupeA-MinIO")
    bucket = os.getenv("MINIO_ENRICHED_BUCKET", MINIO_PROCESSED_BUCKET)
    object_key = os.getenv("MINIO_ENRICHED_PATH", MINIO_ENRICHED_PATH)

    host = endpoint.replace("http://", "").replace("https://", "")
    client = Minio(
        host,
        access_key=access_key,
        secret_key=secret_key,
        secure=endpoint.startswith("https://"),
    )

    target.parent.mkdir(parents=True, exist_ok=True)
    client.fget_object(bucket, object_key, str(target))


def ensure_enriched_csv() -> Path:
    """
    Garantit la présence du dataset enrichi issu de l'ETL.

    Ordre de résolution :
    1. Fichier local `data/processed/weather_processed_enriched.csv` (copie locale du transform)
    2. Téléchargement depuis MinIO `weather-processed/weather_processed_enriched.csv`
    """
    path = ENRICHED_CSV
    if path.exists():
        return path

    if path != LOCAL_ENRICHED_CSV and LOCAL_ENRICHED_CSV.exists():
        return LOCAL_ENRICHED_CSV

    try:
        _download_enriched_from_minio(LOCAL_ENRICHED_CSV)
    except Exception as err:
        raise FileNotFoundError(
            "Dataset enrichi ETL introuvable.\n"
            f"  Attendu localement : {LOCAL_ENRICHED_CSV}\n"
            f"  Ou dans MinIO : {MINIO_PROCESSED_BUCKET}/{MINIO_ENRICHED_PATH}\n"
            "Lancez d'abord : python scripts/run_pipeline.py"
        ) from err

    return LOCAL_ENRICHED_CSV
