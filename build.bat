@echo off
setlocal ENABLEDELAYEDEXPANSION

REM ============================================================
REM  Data Flipper build script
REM  - Data Flipper build script (git-aware build number)
REM  - Creates/uses .\buildenv\ virtualenv
REM  - Generates common\build_info.py (build number, sha, date)
REM  - Builds portable exe with PyInstaller
REM  - Copies editable resources and drivers to dist\
REM ============================================================

REM ---- Settings ----
set APPNAME=DataFlipper
set MAIN=main.py
set SPEC=DataFlipper.spec

REM Drivers inside the repo (copied to dist\drivers\ after build)
set DRIVER_DIR=dataverse_apis\core\automation\sharepoint\drivers

REM Embedded resources (inside exe) and editable copies
set DATA_ARGS=--add-data "resources;resources" --add-data "output;output"

echo.
echo === [1/5] Ensure build virtualenv ===
if not exist "buildenv\Scripts\python.exe" (
    py -m venv buildenv
)
call buildenv\Scripts\activate.bat

echo.
echo === [1.2/5] Install/upgrade build tools ===
python -m pip install --upgrade pip >nul
python -m pip install -U -r requirements.txt pyinstaller

echo.
echo === [2/5] Fetch git tags (for shared build numbers) ===
git fetch --tags 2>nul

echo.
echo === [3/5] Generate version file ===
REM *** IMPORTANT: this line generates common\build_info.py before building ***
python common\write_build_info.py
if errorlevel 1 goto :error

echo.
echo === [4/5] PyInstaller build ===
if exist "%SPEC%" (
    pyinstaller "%SPEC%"
) else (
    pyinstaller --noconsole --onefile --clean --name "%APPNAME%" %DATA_ARGS% "%MAIN%"
)
if errorlevel 1 goto :error

echo.
echo === [5/5] Post-build: copy editable files ===
REM Copy .env (optional, so users can edit UAT/PROD without rebuilding)
if exist "dataverse_apis\.env" copy /Y "dataverse_apis\.env" "dist\.env" >nul

REM Copy resources folder next to the exe, for user-editable mapping etc.
if exist "resources" xcopy /E /I /Y "resources" "dist\resources\" >nul

REM Copy drivers (optional)
if exist "%DRIVER_DIR%" xcopy /E /I /Y "%DRIVER_DIR%" "dist\drivers\" >nul

echo.
echo Build done. Executable in dist\%APPNAME%.exe
echo Version file: common\build_info.py (generated)
echo Editable without recompiling:
echo   - dist\.env
echo   - dist\resources\entity_mapping.xlsx
echo   - dist\drivers\chromedriver.exe / msedgedriver.exe
echo.

REM (optional) Deactivate venv
call buildenv\Scripts\deactivate.bat >nul 2>&1

endlocal
goto :eof

:error
echo.
echo Build FAILED. See error messages above.
call buildenv\Scripts\deactivate.bat >nul 2>&1
endlocal
exit /b 1
