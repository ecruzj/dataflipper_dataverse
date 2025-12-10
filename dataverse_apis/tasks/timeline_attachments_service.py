# logic/services/timeline_attachments_service.py
import os
import sys
import base64
from pathlib import Path
from typing import Dict, List, Optional

from ..core.services.dataverse_client import call_dataverse

# ===== Helpers to align root with SharePoint downloader =====
APP_NAME = "DataFlipper"

def _get_writable_base_dir() -> Path:
    """
    Same logic as the SharePoint downloader:
    - If it's frozen (EXE): try writing next to the .exe file, and if that fails, use %LOCALAPPDATA%\DataFlipper
    - In dev mode: cwd
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        try:
            t = exe_dir / ".perm_test"
            t.write_text("ok", encoding="utf-8")
            t.unlink(missing_ok=True)
            return exe_dir
        except Exception:
            return Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / APP_NAME
    return Path.cwd()

def _downloads_root() -> Path:
    return (_get_writable_base_dir() / "downloads").resolve()

# ===== File helpers =====
_INVALID = '<>:"/\\|?*\0'
def _safe_filename(name: str) -> str:
    if not name:
        return "file"
    out = []
    for ch in name:
        out.append("_" if ch in _INVALID else ch)
    s = "".join(out).strip().rstrip(". ")
    return s or "file"

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _write_b64(dest: Path, b64: str) -> None:
    _ensure_dir(dest.parent)
    dest.write_bytes(base64.b64decode(b64))

# ===== Service =====
MAX_PAGE = 500
PREFER = {"Prefer": f"odata.maxpagesize={MAX_PAGE}"}

class TimelineAttachmentsService:
    """
    Download attachments from the Timeline (Notes and Emails) directly
    within <BASE>/downloads/<ticket_number>/Timeline/(Notes|Emails).
    """
    def __init__(self):
        self.root = _downloads_root()

    # Public API for your current flow
    def download_into_ticket_folder(self, record_id: str, ticket_number: str) -> Dict[str, int]:
        """
        record_id  : GUID of the record (Account/Incident/etc)
        ticket_number: the folder already created by the SharePoint flow
        """
        base = self.root / _safe_filename(ticket_number) / "Timeline"
        notes_dir  = base / "Notes"
        emails_dir = base / "Emails"

        counts = {"notes": 0, "emails": 0}

        # ---- Notes (annotations with file) ----
        for n in self._fetch_note_attachments(record_id):
            fn  = _safe_filename(n.get("filename") or f"note_{n['annotationid']}.bin")
            b64 = n.get("documentbody")
            if b64:
                _write_b64(notes_dir / fn, b64)
                counts["notes"] += 1

        # ---- Emails (activitymimeattachment) ----
        email_map = self._fetch_emails(record_id)  # {email_id: subject}
        for email_id, subject in email_map.items():
            subject_part = _safe_filename(subject)[:120] or "no_subject"
            for att in self._fetch_email_attachments(email_id):
                fn  = _safe_filename(att.get("filename") or f"emailatt_{att['activitymimeattachmentid']}.bin")
                b64 = att.get("body")
                if b64:
                    _write_b64(emails_dir / subject_part / fn, b64)
                    counts["emails"] += 1

        return counts

    # ---- Fetchers ----
    def _fetch_note_attachments(self, record_id: str) -> List[Dict]:
        ep = (
            "annotations"
            f"?$filter=isdocument eq true and _objectid_value eq {record_id}"
            "&$select=annotationid,filename,mimetype,documentbody,filesize,subject,createdon"
            f"&$top={MAX_PAGE}"
        )
        data = call_dataverse(ep, method="GET", headers_extra=PREFER)
        return data.get("value", [])

    def _fetch_emails(self, record_id: str) -> Dict[str, str]:
        ep = (
            "emails"
            f"?$filter=_regardingobjectid_value eq {record_id}"
            "&$select=activityid,subject,createdon"
            "&$orderby=createdon desc"
            f"&$top={MAX_PAGE}"
        )
        data = call_dataverse(ep, method="GET", headers_extra=PREFER)
        return {row["activityid"]: row.get("subject") or "" for row in data.get("value", [])}

    def _fetch_email_attachments(self, email_activity_id: str) -> List[Dict]:
        ep = (
            "activitymimeattachments"
            f"?$filter=_objectid_value eq {email_activity_id}"
            "&$select=activitymimeattachmentid,filename,mimetype,body,filesize"
            f"&$top={MAX_PAGE}"
        )
        data = call_dataverse(ep, method="GET", headers_extra=PREFER)
        return data.get("value", [])