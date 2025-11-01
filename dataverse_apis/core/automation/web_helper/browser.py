import re
import subprocess
from ...logging.logging_conf import get_logger
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

log = get_logger(__name__)

# Option A: Use webdriver-manager to ensure you always download the correct driver.
try:
    from webdriver_manager.chrome import ChromeDriverManager
    _HAS_WDM = True
except Exception:
    _HAS_WDM = False
    ChromeDriverManager = None

DEFAULT_BRAVE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

# def _get_brave_version(brave_path: str = DEFAULT_BRAVE) -> str:
#     """
#     Returns the full version of Chromium used by Brave, e.g. '142.0.7444.60'.
#     """
#     out = subprocess.check_output([brave_path, "--version"], text=True).strip()
#     # Examples: "Brave Browser 1.71.123 Chromium: 142.0.7444.60"
#     m = re.search(r"Chromium:\s*([0-9.]+)", out)
#     if m:
#         return m.group(1)
#     # Some builds return only the Chromium number
#     m2 = re.search(r"\b(\d+\.\d+\.\d+\.\d+)\b", out)
#     return m2.group(1) if m2 else ""

def _get_brave_version(brave_path: str = DEFAULT_BRAVE) -> str:
    """
    Returns Brave's Chromium version, e.g. '142.0.7444.60',
    without launching a visible Brave window.
    """
    import re, subprocess, sys

    # 1) Try Windows Registry (no UI)
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\BraveSoftware\Brave-Browser\BLBeacon"
        ) as key:
            v, _ = winreg.QueryValueEx(key, "version")
            # v is like '1.71.123'; we still want the Chromium part.
            # If you also store Chromium version in build_info, use that; else fallback below.
            # Some Brave builds also write 'promoted-version' but not the Chromium build.
            # We'll fallback to --version for Chromium digits if needed.
            if v:
                # Let Selenium Manager handle major detection if we can't extract Chromium.
                return v
    except Exception:
        pass

    # 2) Fallback: run brave --version but with NO WINDOW
    try:
        creationflags = 0x08000000  # CREATE_NO_WINDOW
        out = subprocess.check_output(
            [brave_path, "--version"],
            text=True,
            creationflags=creationflags  # <-- prevents a visible Brave window
        ).strip()
        # Examples: "Brave Browser 1.71.123 Chromium: 142.0.7444.60"
        m = re.search(r"Chromium:\s*([0-9.]+)", out)
        if m:
            return m.group(1)
        # Fallback: any version-like pattern
        m2 = re.search(r"\b(\d+\.\d+\.\d+\.\d+)\b", out)
        return m2.group(1) if m2 else ""
    except Exception:
        return ""


def make_brave_driver(download_dir: Path, brave_path: str = DEFAULT_BRAVE) -> webdriver.Chrome:
    """
    Create a ChromeDriver for Brave with:
     - Automatic download of the correct driver (if webdriver-manager is installed).
     - Clear error message if there is a version mismatch.
    """
    opts = Options()
    opts.binary_location = brave_path
    opts.add_experimental_option("prefs", {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True
    })

    brave_ver = _get_brave_version(brave_path)
    major = brave_ver.split(".")[0] if brave_ver else ""

    try:
        # first try: webdriver-manager (controlled driver resolution)
        if _HAS_WDM and ChromeDriverManager and major.isdigit():
            log.info(f"[Browser Resolver] Trying webdriver-manager for Brave Chromium major version {major}")
            
            # Download the ChromeDriver that corresponds to the Chromium major (e.g., '142')
            driver_path = ChromeDriverManager(driver_version=major).install()
            
            log.info(f"[Browser Resolver] ✔ Driver resolved using webdriver-manager → {driver_path}")
            print(f"[Browser Resolver] ✔ Driver resolved using webdriver-manager (version {major})")
            return webdriver.Chrome(service=Service(driver_path), options=opts)
        else:
            # Fallback: Let Selenium Manager handle it (Selenium 4.6+)
            # # If it fails, the `except` statement below displays a clear message.
            log.info("[Browser Resolver] webdriver-manager not available — fallback to Selenium Manager")
            print("[Browser Resolver] ⚠ webdriver-manager not available — using Selenium Manager (auto)")
            return webdriver.Chrome(options=opts)

    except SessionNotCreatedException as e:
        msg = (
            
            "❌ Could not start Brave with Selenium.\n\n"
            f"Detected Brave/Chromium version: {brave_ver or 'unknown'}\n"
            "Possible cause: ChromeDriver version mismatch.\n\n"
            "Fix:\n"
            "  1) Update Brave, or\n"
            "  2) Re-run the app so webdriver-manager downloads the correct driver.\n"
        )
        log.error(msg)
        raise WebDriverException(msg) from e
