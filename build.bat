@echo off
setlocal ENABLEDELAYEDEXPANSION

REM === Settings ===
set APPNAME=DataFlipper
set MAIN=main.py

REM Location of drivers in the project
set DRIVER_DIR=dataverse_apis\core\automation\sharepoint\drivers

REM Resources (embedded) and editable will also be copied to dist\
set DATA_ARGS=--add-data "resources;resources" --add-data "output;output"

REM === 1) Create/activate build venv ===
if not exist "buildenv\Scripts\python.exe" (
  py -3 -m venv buildenv
)

call buildenv\Scripts\activate.bat

echo Using Python:
python --version
where python

REM === 2) Install project dependencies in the venv ===
if exist requirements.txt (
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
) else (
  echo [WARN] requirements.txt not found. Make sure you install dependencies manually.
)

REM === 3) Set conditional arguments for drivers (only if they exist) ===
set BIN_ARGS=
if exist "%DRIVER_DIR%\chromedriver.exe" (
  set BIN_ARGS=!BIN_ARGS! --add-binary "%DRIVER_DIR%\chromedriver.exe;drivers"
)
if exist "%DRIVER_DIR%\msedgedriver.exe" (
  set BIN_ARGS=!BIN_ARGS! --add-binary "%DRIVER_DIR%\msedgedriver.exe;drivers"
)

REM === 4) Clean and compile with the venv PyInstaller ===
rmdir /s /q build dist 2>nul

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name %APPNAME% ^
  %DATA_ARGS% ^
  %BIN_ARGS% ^
  "%MAIN%"

REM === 5) External overrides next to the .exe (editable without recompiling) ===
REM .env to change UAT/PROD
if exist "dataverse_apis\.env" copy /Y "dataverse_apis\.env" "dist\.env" >nul

REM editable resources (e.g. resources\entity_mapping.xlsx)
if exist "resources" xcopy /E /I /Y "resources" "dist\resources\" >nul

REM editable drivers (they will have priority over embedded ones)
if exist "%DRIVER_DIR%" xcopy /E /I /Y "%DRIVER_DIR%" "dist\drivers\" >nul

echo.
echo Build done. Executable in dist\%APPNAME%.exe
echo Edit without recompiling:
echo   - dist\.env
echo   - dist\resources\entity_mapping.xlsx
echo   - dist\drivers\chromedriver.exe / msedgedriver.exe
echo.

REM (optional) Disable venv
call buildenv\Scripts\deactivate.bat >nul 2>&1

endlocal
