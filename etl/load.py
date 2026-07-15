#!/usr/bin/env python3
"""
Weather ETL - Load: MinIO processed -> MongoDB Data Warehouse

Ce script :
- lit weather_processed.csv depuis MinIO (bucket processed),
- remplace la collection MongoDB (pas de doublons),
- charge les données dans weather_dwh.weather_observations,
- crée les index utiles pour l'équipe BI.

Prérequis:
    pip install pandas minio python-dotenv pymongo
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from minio import Minio
from pymongo import MongoClient
from pymongo.collection import Collection

# --------------------------------------------------------------------
# Paths / environnement
# --------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

ENV_PATH = PROJECT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

DATA_DIR = PROJECT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

# --------------------------------------------------------------------
# MinIO settings
# --------------------------------------------------------------------

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "groupea_de")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "ForceN-GroupeA-MinIO")
MINIO_PROCESSED_BUCKET = os.getenv("MINIO_PROCESSED_BUCKET", "weather-processed")
MINIO_PROCESSED_PATH = os.getenv("MINIO_PROCESSED_PATH", "weather_processed.csv")

PROCESSED_LOCAL_FALLBACK = PROCESSED_DIR / "weather_processed.csv"

MINIO_HOST = MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
MINIO_SECURE = MINIO_ENDPOINT.startswith("https://")

minio_client = Minio(
    MINIO_HOST,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)

# --------------------------------------------------------------------
# MongoDB settings
# --------------------------------------------------------------------

MONGO_USER = os.getenv("MONGO_USER", "groupea_de")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "ForceN-GroupeA-Mongo")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_DB = os.getenv("MONGO_DB", "weather_dwh")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "weather_observations")


def build_mongo_uri() -> str:
    """Build a MongoDB URI with properly escaped credentials."""
    explicit_uri = os.getenv("MONGO_URI")
    if explicit_uri and not os.getenv("MONGO_USER"):
        return explicit_uri
    user = quote_plus(MONGO_USER)
    password = quote_plus(MONGO_PASSWORD)
    return (
        f"mongodb://{user}:{password}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"
    )


MONGO_URI = build_mongo_uri()

BATCH_SIZE = int(os.getenv("MONGO_BATCH_SIZE", "5000"))

STRING_COLUMNS = ["summary", "precip_type", "daily_summary"]
NUMERIC_COLUMNS = [
    "temperature_c",
    "apparent_temperature_c",
    "humidity",
    "wind_speed_km_per_h",
    "wind_bearing_degrees",
    "visibility_km",
    "pressure_millibars",
]
EXPECTED_COLUMNS = ["date_time", *STRING_COLUMNS, *NUMERIC_COLUMNS]


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def load_processed_dataframe() -> pd.DataFrame:
    """Load the processed CSV from MinIO first, fallback to local file if needed."""
    try:
        response = minio_client.get_object(MINIO_PROCESSED_BUCKET, MINIO_PROCESSED_PATH)
        try:
            df = pd.read_csv(response)
        finally:
            response.close()
            response.release_conn()
        print(f"[OK] Lecture depuis MinIO: {MINIO_PROCESSED_BUCKET}/{MINIO_PROCESSED_PATH}")
        return df
    except Exception as err:
        print(f"[INFO] Lecture MinIO impossible, fallback local: {err}")
        if not PROCESSED_LOCAL_FALLBACK.exists():
            raise FileNotFoundError(
                f"Fichier introuvable: {PROCESSED_LOCAL_FALLBACK}"
            ) from err
        print(f"[OK] Lecture depuis le fichier local: {PROCESSED_LOCAL_FALLBACK}")
        return pd.read_csv(PROCESSED_LOCAL_FALLBACK)


def dataframe_to_documents(df: pd.DataFrame) -> list[dict]:
    """Convert the processed DataFrame into MongoDB-ready documents."""
    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise KeyError(f"Colonnes manquantes dans le CSV: {missing}")

    frame = df[EXPECTED_COLUMNS].copy()
    frame["date_time"] = pd.to_datetime(frame["date_time"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["date_time"])

    for col in STRING_COLUMNS:
        frame[col] = frame[col].astype("string").fillna("")

    for col in NUMERIC_COLUMNS:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    documents: list[dict] = []
    for row in frame.itertuples(index=False):
        doc = {
            "date_time": row.date_time.to_pydatetime(),
            "summary": str(row.summary),
            "precip_type": str(row.precip_type),
            "daily_summary": str(row.daily_summary),
        }
        for col in NUMERIC_COLUMNS:
            value = getattr(row, col)
            doc[col] = None if pd.isna(value) else float(value)
        documents.append(doc)

    return documents


def ensure_indexes(collection: Collection) -> None:
    """Create indexes for BI queries and duplicate prevention."""
    collection.create_index("date_time", unique=True, name="idx_date_time_unique")
    collection.create_index("precip_type", name="idx_precip_type")


def insert_documents(collection: Collection, documents: list[dict]) -> int:
    """Replace collection content and insert documents in batches."""
    collection.drop()
    print(f"[OK] Collection '{MONGO_COLLECTION}' réinitialisée.")

    if not documents:
        print("[WARN] Aucun document à insérer.")
        return 0

    inserted = 0
    for start in range(0, len(documents), BATCH_SIZE):
        batch = documents[start : start + BATCH_SIZE]
        result = collection.insert_many(batch, ordered=True)
        inserted += len(result.inserted_ids)
        print(f"[OK] Lot {start // BATCH_SIZE + 1}: {len(batch)} documents insérés.")

    return inserted


def print_validation(collection: Collection) -> None:
    """Print a short validation summary after load."""
    total = collection.count_documents({})
    sample = collection.find_one({}, {"_id": 0})
    indexes = list(collection.list_indexes())

    print("\n=== Validation MongoDB ===")
    print(f"Base de données     : {MONGO_DB}")
    print(f"Collection          : {MONGO_COLLECTION}")
    print(f"Documents insérés   : {total}")
    print(f"Index créés         : {[idx['name'] for idx in indexes]}")
    if sample:
        print(f"Exemple de document : {sample}")


def main() -> None:
    print("=== Weather ETL - Load MongoDB ===")
    print(f"Source MinIO        : {MINIO_PROCESSED_BUCKET}/{MINIO_PROCESSED_PATH}")
    print(f"Cible MongoDB       : {MONGO_DB}.{MONGO_COLLECTION}")

    df = load_processed_dataframe()
    print(f"Shape CSV           : {df.shape}")

    documents = dataframe_to_documents(df)
    print(f"Documents préparés  : {len(documents)}")

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print("[OK] Connexion MongoDB établie.")

    db = client[MONGO_DB]
    collection = db[MONGO_COLLECTION]

    inserted = insert_documents(collection, documents)
    ensure_indexes(collection)
    print_validation(collection)

    print(f"\nChargement terminé. {inserted} documents insérés dans {MONGO_DB}.{MONGO_COLLECTION}.")


if __name__ == "__main__":
    main()
