from __future__ import annotations
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "common"
BUILD_DIR = ROOT / "build"

def read_app_version() -> str:
    text = (COMMON / "version.py").read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("APP_VERSION"):
            return line.split("=", 1)[1].strip().strip('"\'\'')
    return "0.0.0"

def get_git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT).decode().strip()
    except Exception:
        return "nogit"

def commits_since_version_tag(app_version: str):
    tag = f"v{app_version}"
    try:
        out = subprocess.check_output(["git", "rev-list", f"{tag}..HEAD", "--count"], cwd=ROOT).decode().strip()
        return int(out)
    except Exception:
        return None

def next_build_number() -> int:
    BUILD_DIR.mkdir(exist_ok=True)
    f = BUILD_DIR / "build_number.txt"
    if not f.exists():
        f.write_text("0", encoding="utf-8")
    try:
        current = int((f.read_text(encoding="utf-8") or "0").strip())
    except Exception:
        current = 0
    next_n = current + 1
    f.write_text(str(next_n), encoding="utf-8")
    return next_n

def write_build_info():
    app_version = read_app_version()
    build_number = commits_since_version_tag(app_version)
    if build_number is None:
        build_number = next_build_number()

    git_sha = get_git_sha()
    build_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    full_version = f"{app_version}+{build_number}.{git_sha}"

    out = f'''# Auto-generated at build time. DO NOT COMMIT.
APP_VERSION = "{app_version}"
BUILD_NUMBER = {build_number}
GIT_SHA = "{git_sha}"
BUILD_DATE = "{build_date}"
FULL_VERSION = "{full_version}"
'''
    (COMMON / "build_info.py").write_text(out, encoding="utf-8")
    print(f"[build] App: {app_version} | Build: {build_number} | Git: {git_sha} | Date: {build_date}")
    print(f"[build] FULL_VERSION = {full_version}")

if __name__ == "__main__":
    write_build_info()