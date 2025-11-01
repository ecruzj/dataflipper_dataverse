# tools/write_version_info.py
from pathlib import Path
import re

# Importa tu build_info
from build_info import FULL_VERSION, APP_VERSION, BUILD_NUMBER

# ---- Config de branding ----
COMPANY_NAME = "CSOD"
PRODUCT_NAME = "Data Flipper with Dataverse APIs"
FILE_DESCRIPTION = "Transpose Excel data and fetch related SharePoint documents"
INTERNAL_NAME = "DataFlipper"
ORIGINAL_FILENAME = "DataFlipper.exe"
COPYRIGHT = "© 2025 CSOD"
COMMENTS = "Developed by Josue Cruz"

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "common" / "version_info_template.txt"
TARGET   = ROOT / "common" / "version_info.txt"

def _parse_to_tuple(version_str: str) -> tuple[int, int, int, int]:
    """
    Converts versions like '2.5.6+6.1126ed3' or '2.5.6' into (2,5,6,6)
    """
    # Take only major.minor.patch and an optional build number
    # Prefer BUILD_NUMBER if available; else 0.
    # APP_VERSION is '2.5.6' and BUILD_NUMBER like '6'
    parts = (APP_VERSION or "0.0.0").split(".")
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    # ensure BUILD_NUMBER is a string before applying regex and handle no-match
    build_str = str(BUILD_NUMBER) if BUILD_NUMBER is not None else "0"
    m = re.search(r"\d+", build_str)
    build = int(m.group()) if m else 0
    return (major, minor, patch, build)

def main():
    file_vers = _parse_to_tuple(FULL_VERSION)
    prod_vers = file_vers

    txt = TEMPLATE.read_text(encoding="utf-8")
    txt = (
        txt.replace("{FILE_VERS}", f"{file_vers}")
           .replace("{PROD_VERS}", f"{prod_vers}")
           .replace("{COMPANY_NAME}", COMPANY_NAME)
           .replace("{FILE_DESCRIPTION}", FILE_DESCRIPTION)
           .replace("{FILE_VERSION_STR}", FULL_VERSION)
           .replace("{INTERNAL_NAME}", INTERNAL_NAME)
           .replace("{COPYRIGHT}", COPYRIGHT)
           .replace("{ORIGINAL_FILENAME}", ORIGINAL_FILENAME)
           .replace("{PRODUCT_NAME}", PRODUCT_NAME)
           .replace("{PRODUCT_VERSION_STR}", FULL_VERSION)
           .replace("{COMMENTS}", COMMENTS)
    )

    TARGET.write_text(txt, encoding="utf-8")
    print(f"[version] wrote {TARGET} with FULL_VERSION={FULL_VERSION}")

if __name__ == "__main__":
    main()