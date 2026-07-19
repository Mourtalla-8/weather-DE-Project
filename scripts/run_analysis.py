#!/usr/bin/env python3
"""Vérifie les données ETL et lance l'analyse ML."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

from lib.common import (
    SetupError,
    ensure_python_env,
    log_err,
    log_info,
    log_ok,
    reexec_in_venv,
    run_python_script,
)
from paths import EXPECTED_ROW_COUNT, ensure_enriched_csv, ensure_output_dirs


def verify_enriched_csv() -> None:
    try:
        path = ensure_enriched_csv()
    except FileNotFoundError as err:
        raise SetupError(str(err)) from err

    df = pd.read_csv(path, usecols=["date_time"])
    row_count = len(df)
    if row_count != EXPECTED_ROW_COUNT:
        raise SetupError(
            f"Nombre de lignes inattendu : {row_count} (attendu : {EXPECTED_ROW_COUNT})"
        )
    log_ok(f"Dataset enrichi ETL validé ({row_count:,} lignes) — {path}")


def main() -> int:
    reexec_in_venv()
    print("=== Analyse Weather Data Platform ===")
    try:
        ensure_python_env()
        ensure_output_dirs()
        verify_enriched_csv()

        log_info("Entraînement ML + génération figure")
        run_python_script("analysis/ml/train_predict.py")

        log_ok("Analyse ML terminée")
        log_info("EDA : jupyter notebook analysis/eda/EDA_Analyse_Statistique.ipynb")
        log_info("Viz : jupyter notebook analysis/viz/analyses.ipynb")
        log_info("BI  : streamlit run analysis/bi/app.py")
        return 0
    except SetupError as err:
        log_err(str(err))
        return 1
    except Exception as err:
        log_err(f"Erreur inattendue : {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
