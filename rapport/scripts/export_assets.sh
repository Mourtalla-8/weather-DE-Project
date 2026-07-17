#!/usr/bin/env bash
# Exporte les datasets CSV et le dump MongoDB vers rapport/
# Usage (depuis la racine du projet) : bash rapport/scripts/export_assets.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RAPPORT="$ROOT/rapport"
ENV_FILE="$ROOT/.env"

echo "=== Export assets rapport ==="

# --- CSV ---
RAW_SRC="$ROOT/data/raw/weatherHistory.csv"
PROC_SRC="$ROOT/data/processed/weather_processed.csv"

if [[ ! -f "$RAW_SRC" ]]; then
  RAW_SRC="$ROOT/temp/Repport/weatherHistory.csv"
fi
if [[ ! -f "$PROC_SRC" ]]; then
  PROC_SRC="$ROOT/temp/Repport/weather_processed.csv"
fi

mkdir -p "$RAPPORT/data/raw" "$RAPPORT/data/processed"

if [[ -f "$RAW_SRC" ]]; then
  cp "$RAW_SRC" "$RAPPORT/data/raw/weatherHistory.csv"
  echo "[OK] raw: weatherHistory.csv"
else
  echo "[WARN] weatherHistory.csv introuvable — lancez python scripts/run_pipeline.py"
fi

if [[ -f "$PROC_SRC" ]]; then
  cp "$PROC_SRC" "$RAPPORT/data/processed/weather_processed.csv"
  echo "[OK] processed: weather_processed.csv"
else
  echo "[WARN] weather_processed.csv introuvable"
fi

# --- MongoDB dump ---
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

DUMP_DIR="$RAPPORT/database/dump"
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

# --- Résumé ---
echo ""
echo "=== Résumé ==="
for f in "$RAPPORT/data/raw/weatherHistory.csv" "$RAPPORT/data/processed/weather_processed.csv"; do
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
