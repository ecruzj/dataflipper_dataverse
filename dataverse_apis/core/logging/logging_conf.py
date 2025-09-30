# core/logging_conf.py
import logging
from pathlib import Path
from datetime import datetime
import os, sys
from typing import Optional

from ..services.runtime_paths import resolve_runtime_path

_CONFIGURED = False
_current_log_file: Optional[Path] = None

APP_FALLBACK_NAME = "DataFlipper" # Fallback if not provided in setup_logging

def _writable_logs_dir(app_name: str,
                       override: Path | None = None) -> Path:
    """
    Returns a writable folder for logs in this order:
    0) explicit override or LOG_DIR (env var)
    1) existing 'logs' (detected with resolve_runtime_path("logs"))
    2) dist\logs\ (next to the .exe)
    3) %LOCALAPPDATA%\{app}\logs
    4) cwd\logs
    Creates the folder if it doesn't exist.
    """
    # 0) override / env
    env_dir = os.getenv("LOG_DIR")
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # 1) If 'logs' already exist somewhere known (e.g. next to the .exe), use it
    existing = resolve_runtime_path("logs")
    if existing:
        try:
            p = Path(existing)
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass

    # 2) Along with the .exe (PyInstaller)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidate = exe_dir / "logs"
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            # writing test
            test = candidate / ".write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            return candidate
        except Exception:
            pass

        # 3) %LOCALAPPDATA%\{app}\logs
        base = Path(os.getenv("LOCALAPPDATA", str(Path.home())))
        candidate = base / (app_name or APP_FALLBACK_NAME) / "logs"
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate

    # 4) cwd\logs (dev environment)
    candidate = Path.cwd() / "logs"
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate

# def setup_logging(app_name: str = "dataverse_apis", level: str | None = None, logs_dir: Path | None = None):
#     global _CONFIGURED
#     if _CONFIGURED:
#         return

#     # Level per env var (optional): LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
#     lvl = (level or os.getenv("LOG_LEVEL") or "INFO").upper()

#     # <root>/logs folder
#     project_root = Path(__file__).resolve().parents[1]
#     logs_dir = logs_dir or (project_root / "logs")
#     logs_dir.mkdir(parents=True, exist_ok=True)

#     # Unique name with now timestamp
#     ts = datetime.now().strftime("%Y%m%d_%H%M%S")
#     log_file = logs_dir / f"{app_name}_{ts}.log"

#     fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s :: %(message)s", "%Y-%m-%dT%H:%M:%S%z")

#     file_h = logging.FileHandler(str(log_file), encoding="utf-8")
#     file_h.setFormatter(fmt)

#     console_h = logging.StreamHandler()
#     console_h.setFormatter(fmt)

#     root = logging.getLogger()
#     root.setLevel(lvl)
#     root.addHandler(file_h)
#     root.addHandler(console_h)

#     _CONFIGURED = True

#     logging.getLogger(__name__).info(f"Logging initialized → {log_file}")

def setup_logging(app_name: str = APP_FALLBACK_NAME,
                  level: str | None = None,
                  logs_dir: Path | None = None) -> Path:
    """
    Configures file + console logging. Returns the path to the .log file.
    Only configured once per process.
    """
    global _CONFIGURED, _current_log_file
    if _CONFIGURED:
        return _current_log_file or Path()

    lvl = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    target_dir = _writable_logs_dir(app_name or APP_FALLBACK_NAME, logs_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = target_dir / f"{app_name}_{ts}.log"

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
        "%Y-%m-%dT%H:%M:%S%z",
    )

    root = logging.getLogger()
    root.setLevel(lvl)

    file_h = logging.FileHandler(str(log_file), encoding="utf-8")
    file_h.setFormatter(fmt)

    console_h = logging.StreamHandler()
    console_h.setFormatter(fmt)

    root.addHandler(file_h)
    root.addHandler(console_h)

    _CONFIGURED = True
    _current_log_file = log_file
    root.info(f"Logging initialized → {log_file}")
    return log_file

def get_logger(name: str | None = None) -> logging.Logger:
    """_summary_
        Get one logger per module/area.
        Recommended usage: get_logger(__name__)
    """
    return logging.getLogger(name or "app")
