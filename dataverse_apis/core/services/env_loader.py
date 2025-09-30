from __future__ import annotations
import os
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv, dotenv_values

from .runtime_paths import resolve_runtime_path

CANDIDATES = [".env", "resources/.env"]  # search order

@lru_cache(maxsize=1)
def _load_env() -> dict:
    """Load .env from the first existing location (via resolve_runtime_path)."""
    for rel in CANDIDATES:
        p = resolve_runtime_path(rel)
        if p:
            load_dotenv(p, override=False)
            return {"path": p, "values": dotenv_values(p)}
    # If there is no .env, we return empty (system environment variables will be used)
    return {"path": None, "values": {}}

def get_env_variable_value(key: str, default: str | None = None, *, required: bool = False) -> str | None:
    """Gets a variable by reading .env (if it exists) and then os.environ."""
    data = _load_env()
    val = os.getenv(key)
    if val is None:
        val = data["values"].get(key)  # in case load_dotenv didn't populate os.environ
    if val is None:
        val = default
    if required and (val is None or str(val).strip() == ""):
        src = data["path"] or "<env>"
        raise RuntimeError(f"Missing required env '{key}' (looked in {src})")
    return val

def env_source_path() -> str | None:
    """Actual path from where the .env was loaded (or None if not found)."""
    return _load_env()["path"]
