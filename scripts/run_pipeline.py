#!/usr/bin/env python3
"""Exécute le pipeline ETL complet dans le bon ordre."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (
    SetupError,
    acquire_lock,
    ensure_prerequisites,
    log_err,
    log_info,
    log_ok,
    reexec_in_venv,
    release_lock,
    run_python_script,
    upload_raw_to_minio,
)


def main() -> int:
    reexec_in_venv()
    print("=== Pipeline ETL ===")
    try:
        acquire_lock()
        ensure_prerequisites()

        log_info("1/4 Extract")
        run_python_script("etl/extract.py")

        log_info("2/4 Upload raw → MinIO")
        upload_raw_to_minio()

        log_info("3/4 Transform")
        run_python_script("etl/transform.py")

        log_info("4/4 Load MongoDB")
        run_python_script("etl/load.py")

        log_ok("Pipeline terminé")
        return 0
    except SetupError as err:
        log_err(str(err))
        return 1
    except KeyboardInterrupt:
        log_err("Pipeline interrompu")
        return 130
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())
