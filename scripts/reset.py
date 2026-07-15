#!/usr/bin/env python3
"""Remet le projet dans un état propre (comme le dépôt GitHub)."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (
    LOCK_FILE,
    PROJECT_ROOT,
    SetupError,
    VENV_DIR,
    docker_compose_down,
    log_err,
    log_info,
    log_ok,
    run,
)


def _chmod_writable(path: Path) -> None:
    for root, dirs, files in os.walk(path):
        for name in files + dirs:
            try:
                os.chmod(os.path.join(root, name), stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
            except OSError:
                pass
    try:
        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR)
    except OSError:
        pass


def remove_data_dir() -> None:
    data_dir = PROJECT_ROOT / "data"
    if not data_dir.exists():
        log_ok("Dossier data/ déjà absent")
        return

    try:
        _chmod_writable(data_dir)
        shutil.rmtree(data_dir)
    except OSError:
        log_info("Suppression via Docker (fichiers créés par les conteneurs)")
        run(
            [
                "docker", "run", "--rm",
                "-v", f"{PROJECT_ROOT}:/project",
                "alpine", "sh", "-c", "rm -rf /project/data",
            ],
            quiet=True,
        )

    log_ok("Dossier data/ supprimé")


def remove_venv() -> None:
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)
    log_ok("Environnement virtuel supprimé")


def remove_lock() -> None:
    for lock in (LOCK_FILE, PROJECT_ROOT / "data" / ".pipeline.lock"):
        if lock.exists():
            lock.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset du projet Weather ETL")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Supprime aussi .venv (réinstallation complète requise)",
    )
    args = parser.parse_args()

    print("=== Reset Weather ETL ===")
    try:
        log_info("Arrêt des conteneurs Docker")
        if docker_compose_down():
            log_ok("Services Docker arrêtés")
        else:
            log_info("Docker non disponible ou aucun conteneur actif")

        remove_lock()
        remove_data_dir()

        if args.full:
            remove_venv()

        log_ok("Reset terminé")
        log_info("Relancez : python scripts/setup.py")
        return 0
    except (OSError, SetupError) as err:
        log_err(str(err))
        return 1


if __name__ == "__main__":
    sys.exit(main())
