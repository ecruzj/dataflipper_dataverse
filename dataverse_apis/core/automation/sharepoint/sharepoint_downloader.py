import os
import time
import glob
import zipfile
import sys

from shutil import which
from ...services.runtime_paths import resolve_runtime_path
from ...logging.logging_conf import get_logger
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException

log = get_logger(__name__)
# ------------------------
# Driver Setup
# ------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
chromedriver_path = os.path.join(current_dir, "drivers", "chromedriver.exe")
edgedriver_path = os.path.join(current_dir, "drivers", "msedgedriver.exe")

APP_NAME = "DataFlipper"

def _get_writable_base_dir() -> Path:
    """Returns a writable folder to store downloads folder:
    - EXE: folder for the .exe; if not allowed, it falls to %LOCALAPPDATA%\<APP_NAME>
    - Dev: cwd
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        try:
            # writing test
            t = exe_dir / ".perm_test"
            t.write_text("ok", encoding="utf-8")
            t.unlink(missing_ok=True)
            return exe_dir
        except Exception:
            return Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / APP_NAME
    return Path.cwd()

def _resolve_driver(exe_name: str) -> str:
    """
    Returns the path to the driver:
    - dist/drivers/<exe_name> (editable without recompiling)
    - _MEIPASS/drivers/<exe_name> (embedded)
    - repo drivers/<exe_name> or PATH
    """
    path = resolve_runtime_path(Path("drivers") / exe_name)
    if path:
        return path
    alt = which(exe_name)
    if alt:
        return alt
    raise FileNotFoundError(
        f"WebDriver not found: {exe_name}. "
        f"Place it in 'dist\\drivers\\{exe_name}' or bundle it via PyInstaller."
    )

def brave_exists():
    return os.path.exists(brave_path)

def setup_driver(download_folder):
    prefs = {
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True,
        "download.default_directory": download_folder
    }

    if brave_exists():
        print("Brave detected. Using Brave browser...")
        log.info("Brave detected. Using Brave browser...")
        options = ChromeOptions()
        options.binary_location = brave_path
        options.add_argument("--start-maximized")
        options.add_experimental_option("prefs", prefs)
        
        chromedriver_path = _resolve_driver("chromedriver.exe")
        service = ChromeService(chromedriver_path)
        return webdriver.Chrome(service=service, options=options)
    else:
        print("Using Microsoft Edge...")
        log.info("Using Microsoft Edge...")
        options = EdgeOptions()
        options.add_argument("--start-maximized")
        options.add_experimental_option("prefs", prefs)
        
        edgedriver_path = _resolve_driver("msedgedriver.exe")
        service = EdgeService(edgedriver_path)
        return webdriver.Edge(service=service, options=options)

def is_valid_url(driver):
    # Check if page loaded correctly or returned "Page not found"
    return "Page not found" not in driver.page_source

def is_empty_sharepoint_folder(driver):
    # Check if 'This folder is empty' is present
    try:
        driver.find_element(By.XPATH, "//div[@data-automationid='list-empty-placeholder-title']")
        return True
    except NoSuchElementException:
        return False

def click_download_button(driver):
    # Try to click the visible Download button
    try:
        download_button = driver.find_element(By.XPATH, "//button[@data-automationid='downloadCommand']")
        download_button.click()
        print("Download button clicked directly.")
        log.info("Download button clicked directly.")
    except (NoSuchElementException, ElementNotInteractableException):
        # If not visible, try through the overflow menu
        print("Download button not visible, trying through menu...")
        log.info("Download button not visible, trying through menu...")
        try:
            menu_button = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'More') or contains(@data-automationid, 'more')]")
            menu_button.click()
            time.sleep(1)
            
            download_in_menu = driver.find_element(By.XPATH, "//button[@data-automationid='downloadCommand']")
            download_in_menu.click()
            print("Download button clicked from menu.")
            log.info("Download button clicked from menu.")
        except Exception as e:
            print(f"Failed to click Download button: {e}")
            log.error(f"Failed to click Download button: {e}")

def wait_for_download(download_dir: str,
                    stable_for: float = 8.0,
                    poll: float = 1.0,
                    partial_exts=(".crdownload", ".part", ".tmp")) -> str:
    """
    Wait indefinitely until the download in `download_dir` is complete.
    Criteria:
    1) There must be no 'partial' files (typical browser extensions).
    2) There must be at least one .zip file, and its size must remain stable for `stable_for` seconds.

    Returns the absolute path of the fully downloaded ZIP file (the most recent one).
    """
    download_dir = Path(download_dir)

    def partials_present() -> bool:
        for ext in partial_exts:
            if any(download_dir.glob(f"*{ext}")):
                return True
        return False

    def newest_zip() -> Path | None:
        zips = list(download_dir.glob("*.zip"))
        if not zips:
            return None
        # The most recent by mtime
        return max(zips, key=lambda p: p.stat().st_mtime)

    # Wait for a ZIP to appear and the partials to disappear
    while True:
        nz = newest_zip()
        if nz and not partials_present():
            # We check size stability
            last_size = nz.stat().st_size
            last_change = time.time()
            while True:
                time.sleep(poll)
                # If partials appear again, we restart the external cycle
                if partials_present():
                    break
                nz_now = newest_zip()
                # If a newer ZIP appeared, we switch to that one
                if nz_now and nz_now != nz:
                    nz = nz_now
                    last_size = nz.stat().st_size
                    last_change = time.time()
                    continue
                # Check size
                size_now = nz.stat().st_size
                if size_now != last_size:
                    last_size = size_now
                    last_change = time.time()
                else:
                    # stable size by 'stable_for'
                    if time.time() - last_change >= stable_for:
                        return str(nz.resolve())
        time.sleep(poll)

def ensure_unique_path(path: str) -> Path:
    """If 'path' exists, returns 'path' with suffixes (2), (3), ... until it does not exist."""
    path = Path(path) # Ensure it's a Path object
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix  # e.g., '.zip'
    n = 2
    while True:
        candidate = path.with_name(f"{stem} ({n}){suffix}")
        if not candidate.exists():
            return candidate
        n += 1

def merge_zip_into_existing(existing_zip_path: str, incoming_zip_path: str) -> dict:
    """
    Merges the contents of incoming_zip_path into existing_zip_path.
    - Skips duplicate directories and files (same internal name).
    - Maintains the internal folder structure.
    - Returns a summary with counters.
    """
    added = 0
    skipped = 0

    with zipfile.ZipFile(existing_zip_path, mode="a", compression=zipfile.ZIP_DEFLATED) as zout:
        existing_names = set(zout.namelist())

        with zipfile.ZipFile(incoming_zip_path, mode="r") as zin:
            for info in zin.infolist():
                # Skip directory entries
                if info.is_dir():
                    continue

                name_in_zip = info.filename

                # Avoid duplicates
                if name_in_zip in existing_names:
                    skipped += 1
                    continue

                # Copy content (stream) and respect basic timestamps
                with zin.open(info, "r") as src:
                    data = src.read()

                new_info = zipfile.ZipInfo(filename=name_in_zip, date_time=info.date_time)
                new_info.compress_type = zipfile.ZIP_DEFLATED
                # Optional: preserve unix permissions if you are interested
                new_info.external_attr = info.external_attr

                zout.writestr(new_info, data)
                existing_names.add(name_in_zip)
                added += 1

    return {"added": added, "skipped": skipped}

def download_from_sharepoint(url, folder_name):
    # Temp path for downloading (shared for all iterations)
    # base_download_path = os.path.join(current_dir, "downloads", "temp")
    run_base = _get_writable_base_dir()
    base_download_path = str((run_base / "downloads" / "temp").resolve())
    os.makedirs(base_download_path, exist_ok=True)

    # Setup WebDriver
    driver = setup_driver(base_download_path)

    # (Optional but recommended in modern headless Chrome/Edge)
    # Allow headless downloads:
    try:
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": base_download_path
        })
    except Exception:
        pass

    driver.get(url)
    time.sleep(5)

    log.info(f"{folder_name} - Accessing SharePoint URL: {url}")

    if not is_valid_url(driver):
        print(f"Invalid URL or 'Page not found': {url}")
        log.error(f"Invalid URL or 'Page not found': {url}")
        driver.quit()
        return

    if is_empty_sharepoint_folder(driver):
        print(f"No files in SharePoint folder: {folder_name}")
        log.info(f"No files in SharePoint folder: {folder_name}")
        driver.quit()
        return

    # Clean residue from previous downloads in temp (optional)
    for p in glob.glob(os.path.join(base_download_path, "*")):
        try:
            os.remove(p)
        except OSError:
            pass

    # Trigger download
    click_download_button(driver)

    # Wait indefinitely until the ZIP is complete
    try:
        downloaded_file = wait_for_download(base_download_path, stable_for=8.0, poll=1.0)

        if downloaded_file:
            # Final folder and destination zip
            # final_folder = os.path.join(current_dir, "downloads", folder_name)
            final_folder = str((run_base / "downloads" / folder_name).resolve())
            os.makedirs(final_folder, exist_ok=True)

            desired_path = os.path.join(final_folder, "Related Documents.zip")

            if os.path.exists(desired_path):
                # Zip already exists -> merge contents and delete the new one
                summary = merge_zip_into_existing(desired_path, downloaded_file)
                msg = (f"Merged into existing ZIP: {desired_path} | "
                    f"Added: {summary['added']} | Skipped duplicates: {summary['skipped']}")
                print(msg)
                log.info(msg)
                try:
                    os.remove(downloaded_file)
                except OSError:
                    pass
            else:
                # Does not exist -> move/rename
                os.replace(downloaded_file, desired_path)
                print(f"Download complete and moved to: {desired_path}")
                log.info(f"Download complete and moved to: {desired_path}")
        else:
            # In theory, we shouldn't get here because we're waiting indefinitely,
            # but we're leaving it for safety.
            print(f"Download did not complete for: {folder_name}")
            log.error(f"Download did not complete for: {folder_name}")
    finally:
        driver.quit()
        
def extract_related_zip(folder_name: str, remove_zip: bool = True) -> bool:
    """
    Extracts 'Related Documents.zip' to the same folder and (optional) deletes the ZIP file.
    Returns True if it extracted something, False if no ZIP file was found.
    """
    run_base = _get_writable_base_dir()
    dest_folder = Path((run_base / "downloads" / folder_name).resolve())
    zip_path = Path(dest_folder / "Related Documents.zip")

    if not zip_path.exists():
        log.info(f"No ZIP to extract for {folder_name}: {zip_path} not found")
        return False

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(dest_folder)
        if remove_zip:
            zip_path.unlink(missing_ok=True)
        log.info(f"Extracted ZIP for {folder_name} to {dest_folder} (removed_zip={remove_zip})")
        return True
    except Exception as e:
        log.error(f"Failed to extract ZIP for {folder_name}: {e}")
        return False