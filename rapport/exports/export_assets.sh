#!/usr/bin/env bash
# Exporte les datasets CSV et le dump MongoDB vers rapport/exports/
# Usage (depuis la racine du projet) : bash rapport/exports/export_assets.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
EXPORTS="$ROOT/rapport/exports"
ENV_FILE="$ROOT/.env"

echo "=== Export assets rapport ==="

RAW_SRC="$ROOT/data/raw/weatherHistory.csv"
PROC_SRC="$ROOT/data/processed/weather_processed.csv"
ENRICHED_SRC="$ROOT/data/processed/weather_processed_enriched.csv"

mkdir -p "$EXPORTS/data/raw" "$EXPORTS/data/processed"

if [[ -f "$RAW_SRC" ]]; then
  cp "$RAW_SRC" "$EXPORTS/data/raw/weatherHistory.csv"
  echo "[OK] raw: weatherHistory.csv"
else
  echo "[WARN] weatherHistory.csv introuvable — lancez python scripts/run_pipeline.py"
fi

if [[ -f "$PROC_SRC" ]]; then
  cp "$PROC_SRC" "$EXPORTS/data/processed/weather_processed.csv"
  echo "[OK] processed: weather_processed.csv"
else
  echo "[WARN] weather_processed.csv introuvable"
fi

if [[ -f "$ENRICHED_SRC" ]]; then
  cp "$ENRICHED_SRC" "$EXPORTS/data/processed/weather_processed_enriched.csv"
  echo "[OK] enriched: weather_processed_enriched.csv"
else
  echo "[WARN] weather_processed_enriched.csv introuvable"
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

MONGO_USER="${MONGO_USER:-groupea_de}"
MONGO_PASSWORD="${MONGO_PASSWORD:-ForceN-GroupeA-Mongo}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-weather_dwh}"

if ! command -v mongodump &>/dev/null; then
  echo "[WARN] mongodump introuvable — installez mongodb-tools"
  exit 0
fi

DUMP_DIR="$EXPORTS/database/dump"
rm -rf "$DUMP_DIR"
mkdir -p "$DUMP_DIR"

mongodump \
  --host="$MONGO_HOST" \
  --port="$MONGO_PORT" \
  --username="$MONGO_USER" \
  --password="$MONGO_PASSWORD" \
  --authenticationDatabase=admin \
  --db="$MONGO_DB" \
  --out="$DUMP_DIR"

echo "[OK] mongodump → $DUMP_DIR/$MONGO_DB/"

echo ""
echo "=== Résumé ==="
for f in "$EXPORTS/data/raw/weatherHistory.csv" \
         "$EXPORTS/data/processed/weather_processed.csv" \
         "$EXPORTS/data/processed/weather_processed_enriched.csv"; do
  if [[ -f "$f" ]]; then
    echo "  $(du -h "$f" | cut -f1)  $f"
  fi
done
if [[ -d "$DUMP_DIR/$MONGO_DB" ]]; then
  echo "  $(du -sh "$DUMP_DIR/$MONGO_DB" | cut -f1)  $DUMP_DIR/$MONGO_DB/"
  if command -v mongosh &>/dev/null; then
    COUNT=$(mongosh --quiet \
      --username="$MONGO_USER" --password="$MONGO_PASSWORD" \
      --authenticationDatabase admin \
      --eval "db.getSiblingDB('$MONGO_DB').weather_observations.countDocuments()" 2>/dev/null || echo "?")
    echo "  Documents weather_observations : $COUNT (attendu : 96429)"
  fi
fi
