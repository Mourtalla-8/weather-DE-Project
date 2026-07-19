#!/usr/bin/env python3
"""Configuration initiale après clone GitHub."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.common import (
    SetupError,
    check_docker,
    check_ports,
    check_python_version,
    ensure_infrastructure,
    ensure_python_env,
    log_err,
    log_info,
    log_ok,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Configuration initiale du projet")
    parser.add_argument(
        "--with-analysis",
        action="store_true",
        help="Installe aussi les dépendances analyse (EDA, ML, Streamlit)",
    )
    args = parser.parse_args()

    print("=== Setup Weather Data Platform ===")
    try:
        check_python_version()
        check_docker()
        check_ports()
        ensure_python_env(install=True, with_analysis=args.with_analysis)
        ensure_infrastructure()
        log_ok("Projet prêt")
        log_info("Étape suivante : python scripts/run_pipeline.py")
        if args.with_analysis:
            log_info("Puis analyse : python scripts/run_analysis.py")
        return 0
    except SetupError as err:
        log_err(str(err))
        return 1


if __name__ == "__main__":
    sys.exit(main())
