"""Utilitaires partagés pour les scripts du projet."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / ".venv"
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
LOCK_FILE = PROJECT_ROOT / ".pipeline.lock"

MIN_PYTHON = (3, 11)
REQUIRED_PORTS = (27017, 9000, 9001, 8443)
HEALTHY_SERVICES = ("mongodb", "minio")


class SetupError(Exception):
    """Erreur bloquante pour les scripts d'orchestration."""


def log_ok(message: str) -> None:
    print(f"[OK] {message}")


def log_err(message: str) -> None:
    print(f"[ERREUR] {message}", file=sys.stderr)


def log_info(message: str) -> None:
    print(f"-> {message}")


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    quiet: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            check=check,
            text=True,
            capture_output=quiet,
        )
    except subprocess.CalledProcessError as err:
        output = (err.stderr or err.stdout or "").strip()
        detail = f" : {output}" if output else ""
        raise SetupError(f"Commande échouée ({' '.join(cmd)}){detail}") from err


def python_executable() -> Path:
    if VENV_DIR.exists():
        for candidate in (VENV_DIR / "bin" / "python", VENV_DIR / "Scripts" / "python.exe"):
            if candidate.exists():
                return candidate
    return Path(sys.executable)


def reexec_in_venv() -> None:
    """Relance le script avec le Python du venv si nécessaire."""
    target = python_executable()
    if not VENV_DIR.exists() or not target.exists():
        return
    if Path(sys.prefix).resolve() == VENV_DIR.resolve():
        return
    os.execv(str(target), [str(target), *sys.argv])


def check_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        raise SetupError(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ requis (actuel : {sys.version.split()[0]})"
        )
    log_ok(f"Python {sys.version.split()[0]}")


def check_docker() -> None:
    if not shutil.which("docker"):
        raise SetupError("Docker introuvable — installez Docker Desktop ou Docker Engine.")
    run(["docker", "info"], quiet=True)
    run(["docker", "compose", "version"], quiet=True)
    log_ok("Docker et Docker Compose disponibles")


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def check_ports() -> None:
    busy = [port for port in REQUIRED_PORTS if port_in_use(port)]
    if busy:
        log_info(f"Ports occupés : {busy} (services peut-être déjà démarrés)")


def ensure_env_file() -> None:
    if ENV_FILE.exists():
        log_ok(".env présent")
        return
    if not ENV_EXAMPLE.exists():
        raise SetupError(".env.example introuvable")
    shutil.copy(ENV_EXAMPLE, ENV_FILE)
    log_ok(".env créé depuis .env.example")


def ensure_venv() -> None:
    if VENV_DIR.exists():
        log_ok("Environnement virtuel présent")
        return
    log_info("Création de .venv")
    run([sys.executable, "-m", "venv", str(VENV_DIR)])
    log_ok("Environnement virtuel créé")


def install_requirements() -> None:
    if not REQUIREMENTS.exists():
        raise SetupError("requirements.txt introuvable")
    pip_name = "pip.exe" if os.name == "nt" else "pip"
    pip = python_executable().parent / pip_name
    run([str(pip), "install", "-q", "-r", str(REQUIREMENTS)], quiet=True)
    log_ok("Dépendances Python installées")


def ensure_data_dirs() -> None:
    """Crée data/ et sous-dossiers avec les bonnes permissions avant Docker."""
    for sub in ("raw", "processed", "mongo", "minio", "nifi"):
        (PROJECT_ROOT / "data" / sub).mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(PROJECT_ROOT / "data", 0o755)
    except OSError:
        pass


def docker_compose_up() -> None:
    if not COMPOSE_FILE.exists():
        raise SetupError("docker-compose.yml introuvable")
    if not ENV_FILE.exists():
        raise SetupError(".env introuvable — relancez setup.py")
    ensure_data_dirs()
    run(["docker", "compose", "up", "-d"], quiet=True)
    log_ok("Services Docker démarrés")


def docker_compose_down() -> bool:
    """Arrête les conteneurs. Retourne False si Docker indisponible."""
    if not shutil.which("docker") or not COMPOSE_FILE.exists():
        return False
    result = subprocess.run(
        ["docker", "compose", "down"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def _service_status(service: str) -> tuple[str | None, str | None]:
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json", service],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None, None
    try:
        data = json.loads(result.stdout.strip().splitlines()[0])
    except (json.JSONDecodeError, IndexError):
        return None, None
    return data.get("Health"), data.get("State")


def service_ready(service: str) -> bool:
    health, state = _service_status(service)
    if health == "healthy":
        return True
    if state == "running" and health in (None, ""):
        return True
    return False


def port_reachable(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(2)
        return sock.connect_ex((host, port)) == 0


def infrastructure_ready() -> bool:
    return (
        all(service_ready(name) for name in HEALTHY_SERVICES)
        and port_reachable(27017)
        and port_reachable(9000)
    )


def wait_for_services(timeout: int = 120) -> None:
    log_info("Attente MongoDB (27017) et MinIO (9000)")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if infrastructure_ready():
            log_ok("MongoDB et MinIO prêts")
            return
        time.sleep(3)
    status = {
        name: _service_status(name) for name in HEALTHY_SERVICES
    }
    status["port_27017"] = port_reachable(27017)
    status["port_9000"] = port_reachable(9000)
    raise SetupError(f"Services non prêts : {status}")


def services_running() -> bool:
    return infrastructure_ready()


def acquire_lock() -> None:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            raise SetupError(
                "Pipeline déjà en cours — supprimez .pipeline.lock si bloqué"
            )
        except ProcessLookupError:
            LOCK_FILE.unlink(missing_ok=True)
        except (ValueError, PermissionError):
            try:
                os.chmod(LOCK_FILE, 0o644)
                LOCK_FILE.unlink(missing_ok=True)
            except OSError as err:
                raise SetupError(
                    "Lock inaccessible — supprimez .pipeline.lock manuellement"
                ) from err
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")


def release_lock() -> None:
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


def run_python_script(relative_path: str) -> None:
    script = PROJECT_ROOT / relative_path
    if not script.exists():
        raise SetupError(f"Script introuvable : {relative_path}")
    run([str(python_executable()), str(script)])


def load_dotenv() -> None:
    if not ENV_FILE.exists():
        raise SetupError(".env introuvable — lancez scripts/setup.py")
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def upload_raw_to_minio() -> None:
    load_dotenv()
    raw_file = PROJECT_ROOT / "data" / "raw" / "weatherHistory.csv"
    if not raw_file.exists():
        raise SetupError("data/raw/weatherHistory.csv introuvable après extract")

    if not port_reachable(9000):
        raise SetupError(
            "MinIO injoignable sur localhost:9000 — lancez : python scripts/setup.py"
        )

    from minio import Minio

    endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "groupea_de")
    secret_key = os.getenv("MINIO_SECRET_KEY", "ForceN-GroupeA-MinIO")
    bucket = os.getenv("MINIO_RAW_BUCKET", "weather-lake")
    object_key = os.getenv("MINIO_RAW_PATH", "raw/weatherHistory.csv")

    host = endpoint.replace("http://", "").replace("https://", "")
    client = Minio(
        host,
        access_key=access_key,
        secret_key=secret_key,
        secure=endpoint.startswith("https://"),
    )

    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        client.fput_object(bucket, object_key, str(raw_file), content_type="text/csv")
    except Exception as err:
        raise SetupError(
            f"Upload MinIO échoué ({endpoint}) — vérifiez Docker : docker compose ps"
        ) from err

    log_ok(f"Raw uploadé → {bucket}/{object_key}")


def verify_packages() -> bool:
    """Vérifie que les dépendances ETL essentielles sont importables."""
    for package in ("minio", "pandas", "pymongo", "kagglehub", "dotenv"):
        try:
            __import__(package)
        except ImportError:
            return False
    return True


def ensure_python_env(*, install: bool = False) -> None:
    """Garantit .env, .venv et les dépendances Python."""
    ensure_env_file()
    ensure_venv()
    reexec_in_venv()
    if install or not verify_packages():
        if install:
            log_info("Installation des dépendances")
        else:
            log_info("Installation des dépendances manquantes")
        install_requirements()
    if not verify_packages():
        raise SetupError("Dépendances Python incomplètes — relancez scripts/setup.py")
    log_ok("Dépendances Python vérifiées")


def ensure_infrastructure() -> None:
    """Garantit que Docker tourne et que MongoDB/MinIO sont prêts."""
    check_docker()
    if not services_running():
        log_info("Démarrage des services Docker")
        docker_compose_up()
    wait_for_services(timeout=120)


def ensure_prerequisites(*, require_venv: bool = True, require_services: bool = True) -> None:
    check_python_version()
    if require_venv:
        ensure_python_env()
    else:
        ensure_env_file()
    if require_services:
        ensure_infrastructure()
