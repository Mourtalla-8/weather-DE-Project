#!/usr/bin/env python3
"""Configuration initiale après clone GitHub."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (
    SetupError,
    check_docker,
    check_ports,
    check_python_version,
    ensure_python_env,
    ensure_infrastructure,
    log_err,
    log_info,
    log_ok,
)


def main() -> int:
    print("=== Setup Weather ETL ===")
    try:
        check_python_version()
        check_docker()
        check_ports()
        ensure_python_env(install=True)
        ensure_infrastructure()
        log_ok("Projet prêt")
        log_info("Étape suivante : python scripts/run_pipeline.py")
        return 0
    except SetupError as err:
        log_err(str(err))
        return 1


if __name__ == "__main__":
    sys.exit(main())
