# Data Flipper (Dataverse + SharePoint)

A Windows desktop tool (PySide6) that:
- **Transposes** Excel files and exports PDFs (separate, combined, or per Excel).
- **Fetches related documents** from SharePoint based on records found in those Excels (via Dataverse lookups).
- Shows a **live progress bar** and detailed logs.

> Repository: https://github.com/ecruzj/dataflipper_dataverse

---

## Features

- **Process Type**
  - **Only Transpose Data** – run the PDF pipeline only.
  - **Transpose Data and Get Related Documents** – run both PDF pipeline and SharePoint retrieval.
  - **Get Only Related Documents from SharePoint** – skip PDFs and fetch SharePoint docs only.

- **Export Mode (PDF)**
  - **Separate PDFs (one per sheet)**
  - **Single Combined PDF**
  - **PDF by Excel file**

- **User Information** panel (email + environment), hidden when “Only Transpose Data” is selected.
- **Entity mapping** from Excel (no hardcode): `Entity`, `Sharepoint Doc (Y/N)`, `Column Name`.
- **SharePoint downloads** are zipped, then automatically unzipped; the `.zip` is removed after extraction.
- **Progress bar** with real-time updates.

---

## Requirements

- Windows 10/11
- Python 3.10+ (3.12 recommended)
- Access to Microsoft **Dataverse** & **SharePoint**
- Azure AD app registration (public client) for interactive auth

---

## Project Layout (high level)

```
dataverse_apis/         # Dataverse & SharePoint helpers, auth, tasks
logic/                  # App business logic (transpose, PDFs, related docs service)
ui/                     # Qt Designer .ui files (compiled to Python for runtime)
resources/              # Optional assets (e.g., entity_mapping.xlsx sample)
downloads/, output/, logs/  # Runtime outputs (not committed)
main.py                 # App entry point (PySide6 UI)
worker_thread.py        # Background processing + progress updates
requirements.txt
```

---

## Setup

### 1) Clone the repo

```powershell
git clone https://github.com/ecruzj/dataflipper_dataverse.git
cd dataflipper_dataverse
```

### 2) Create a virtual environment & install dependencies (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3) Configure environment variables

Copy the sample and fill in your tenant info (do **not** commit your real `.env`):

```powershell
copy dataverse_apis\.env.sample dataverse_apis\.env
notepad dataverse_apis\.env
```

`.env.sample` content (placeholders you must replace):
```ini
# Azure AD Auth
CLIENT_ID=<your-public-client-id>
TENANT_ID=<your-tenant-id-guid>
API_VERSION=9.2
USERNAME=<user@yourdomain.com>
USERDNSDOMAIN=<yourdomain.com>

# Dataverse
DATAVERSE_BASE_URI=https://<org>.crm3.dynamics.com

# SharePoint
SHAREPOINT_BASE_URL=https://<tenant>.sharepoint.com
SHAREPOINT_SITE_PATH=/sites/<site-collection>/
LOCATION_QUERY=sharepointdocumentlocations?$filter=_regardingobjectid_value eq {object_id}

# Optional: override location of the entity mapping file
# ENTITY_MAP_XLSX=resources/entity_mapping.xlsx
```

### 4) (Optional) Entity mapping Excel

Provide an `entity_mapping.xlsx` with columns:
- `Entity` (e.g., `Account`, `Case`, `eCase`, `Inspection`, `Investigation`)
- `Sharepoint Doc` (`Y` / `N`)
- `Column Name` (the column in the Excel that contains the ticket/number/title)

**Search order** at runtime:
1. `ENTITY_MAP_XLSX` (if set in `.env`)
2. `{Selected Main Folder}\entity_mapping.xlsx`
3. `resources\entity_mapping.xlsx`

---

## Run the app

```powershell
python main.py
```

1. Select your **Main Folder** containing the Excel files.
2. Choose a **Process Type** and **Export Mode**.
3. Click **Process Files**.

The progress bar updates as the job moves through Excel parsing, PDF generation, Dataverse lookups, SharePoint downloads, and ZIP extraction.

---

## What the app does (high level)

1. **Excel ingestion** – reads all Excel files in the chosen folder.
2. **Entity detection** – the first word of each filename is matched against `Entity` in the mapping.
3. **Ticket extraction** – reads the mapped `Column Name` in each sheet and collects unique tickets (global uniqueness).
4. **Dataverse lookups** – resolves each ticket to an `object_id`:
   - `account` → `accounts?$filter=accountnumber eq '...'` → `accountid`
   - `case` → `incidents?$filter=ticketnumber eq '...'` → `incidentid`
   - `ecase` → `icps_ecases?$filter=icps_name eq '...'` → `icps_ecaseid`
   - `inspection` → `icps_inspections?$filter=icps_name eq '...'` → `icps_inspectionid`
   - `investigation` → `icps_investigations?$filter=icps_name eq '...'` → `icps_investigationid`
5. **SharePoint URLs** – for each `object_id`, queries locations and builds final folder URLs.
6. **Download & unzip** – downloads all related docs, merges into a ZIP per ticket, then extracts and deletes the ZIP.
7. **PDF generation** – transposes and exports PDFs as selected (separate, combined, per Excel).

---

## Outputs

- PDFs: `output/`
- SharePoint files: `downloads/<ticket_number>/...`
  - Final archive: `Related Documents.zip` (extracted and removed after unzip)
- Logs: `logs/`

---

## Building a portable EXE (optional, PyInstaller)

Use your provided spec or a basic command:

```powershell
pyinstaller --noconsole --onefile --name DataFlipper main.py
# or run the provided build script if present:
.uild.bat
```

The executable is created under `dist/`.

> Tip: include `resources/` via `--add-data` if needed by your runtime path resolver.

---

## Troubleshooting

- **Auth prompts**: ensure your AAD user has permissions for Dataverse and SharePoint.
- **401/403**: double-check `CLIENT_ID`, `TENANT_ID`, and resource permissions.
- **No records for a ticket**: verify `entity_mapping.xlsx` and Excel header names.
- **Nothing downloads**: confirm `_regardingobjectid_value` is correct in `LOCATION_QUERY` and that SharePoint document locations exist for the `object_id`.
- **Progress bar doesn’t move**: verify the background worker is running and emitting `progress_updated` signals; long SharePoint downloads can appear as fewer, larger steps.

---

## Security & Git hygiene

- Never commit real secrets – `.env` is ignored by `.gitignore`.
- Only commit `.env.sample` with placeholders.
- Folders like `build/`, `dist/`, `downloads/`, `output/`, `logs/`, and virtual environments are ignored to keep the repo lightweight.

---

## License

This code is provided for demonstration and internal use. Add your preferred license here.
