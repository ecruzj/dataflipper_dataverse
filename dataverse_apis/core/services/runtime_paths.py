from __future__ import annotations
import sys, inspect
from pathlib import Path
from typing import Optional

def resolve_runtime_path(rel_path: str | Path) -> Optional[str]:
    """Search for a relative resource (e.g., 'resources/entity_mapping.xlsx' or 'drivers/chromedriver.exe')
    in this order:
    1) Next to the .exe (PyInstaller --onefile/--onedir)
    2) _MEIPASS folder (embedded with --add-data/--add-binary)
    3) Current working directory (cwd)
    4) Caller folder (file that called this function) and its parents
    5) THIS module's folder and its parents

    Returns str with the found path, or None if it doesn't exist anywhere.
    """
    rel_path = Path(rel_path)

    candidates: list[Path] = []

    # 1) Next to the .exe
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates.append(exe_dir / rel_path)
        # 2) _MEIPASS (bundled)
        if hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS) / rel_path)

    # 3) CWD
    candidates.append(Path.cwd() / rel_path)

    # 4) Caller dir and its parents
    try:
        caller_file = Path(inspect.stack()[1].filename).resolve()
        caller_bases = [caller_file.parent, *caller_file.parents]
        candidates.extend(base / rel_path for base in caller_bases)
    except Exception:
        pass

    # 5) This module dir and its parents
    this_file = Path(__file__).resolve()
    this_bases = [this_file.parent, *this_file.parents]
    candidates.extend(base / rel_path for base in this_bases)

    # Return first existing
    for p in candidates:
        if p.exists():
            return str(p)

    return None