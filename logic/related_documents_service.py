from __future__ import annotations
import os
from dataclasses import dataclass, asdict, field
from typing import Callable, Iterable, List, Dict, Any
from dataverse_apis.core.automation.sharepoint.sharepoint_downloader import download_from_sharepoint, extract_related_zip, save_metadata_to_excel
from dataverse_apis.core.services.dataverse_client import call_dataverse
from dataverse_apis.tasks.sharepoint_documents import build_sharepoint_folder_url, get_relativeurls_for_object_id
from dataverse_apis.tasks.timeline_attachments_service import TimelineAttachmentsService

# --- Simple and extensible model ---
@dataclass
class Target:
    entity: str
    ticket_number: str
    file: str = ""
    sheet: str = ""
    column: str = ""
    object_id: str | None = None
    relative_urls: List[str] = field(default_factory=list)
    sharepoint_urls: List[str] = field(default_factory=list)

def to_targets(items: Iterable[Dict[str, Any]]) -> List[Target]:
    """Converts a list of dicts to Target dataclasses."""
    out: List[Target] = []
    for d in items:
        out.append(
            Target(
                entity=str(d.get("entity", "")).strip(),
                ticket_number=str(d.get("ticket_number", "")).strip(),
                file=str(d.get("file", "")),
                sheet=str(d.get("sheet", "")),
                column=str(d.get("column", "")),
                object_id=d.get("object_id"),
                relative_urls=list(d.get("relative_urls", [])) if d.get("relative_urls") else [],
                sharepoint_urls=list(d.get("sharepoint_urls", [])) if d.get("sharepoint_urls") else [],
            )
        )
    return out

def to_dicts(items: Iterable[Target]) -> List[Dict[str, Any]]:
    """Convert Targets back to dicts"""
    return [asdict(t) for t in items]

class RelatedDocumentsService:
    def __init__(self, dv_call: Callable[..., Any] = call_dataverse,
                 logger: Callable[[str], None] | None = None,
                 relurl_resolver: Callable[[str], List[str]] = get_relativeurls_for_object_id,
                 sp_url_builder: Callable[[str, str], str] = build_sharepoint_folder_url,
                 sp_downloader: Callable[[str, str, bool], Any] = download_from_sharepoint) -> None:
        self.dv_call = dv_call
        self.log = logger or (lambda msg: None)
        self.relurl_resolver = relurl_resolver
        self.sp_url_builder = sp_url_builder
        self.sp_downloader = sp_downloader
        
     # ————— helpers —————
    @staticmethod
    def _dedupe_keep_order(seq: Iterable[str]) -> List[str]:
        seen, out = set(), []
        for x in seq:
            if x not in seen:
                seen.add(x); out.append(x)
        return out
    
    # 1) get object_id by entidad/ticket_number
    def resolve_object_ids(self, targets: List[Target]) -> List[Target]:
        """Iterate targets and add .object_id based on the entity."""
        if not self.dv_call:
            raise RuntimeError("No dv_call is set in ObjectIdResolver.")
        
        # -------------------- internal helpers --------------------    
        def _odata_quote(value: str) -> str:
            """Escape single quotes for OData and wrap in quotes."""
            v = (value or "").replace("'", "''")
            return f"'{v}'"

        def _build_endpoint_and_id_field(ent: str, key: str) -> tuple[str | None, str | None]:
            q = _odata_quote
            if ent == "account":
                return (f"accounts?$select=accountid&$filter=accountnumber eq {q(key)}",
                        "accountid")
            if ent == "case":
                return (f"incidents?$select=incidentid&$filter=ticketnumber eq {q(key)}",
                        "incidentid")
            if ent == "ecase":
                return (f"icps_ecases?$select=icps_ecaseid&$filter=icps_name eq {q(key)}",
                        "icps_ecaseid")
            if ent == "inspection":
                return (f"icps_inspections?$select=icps_inspectionid&$filter=icps_name eq {q(key)}",
                        "icps_inspectionid")
            if ent == "investigation":
                return (f"icps_investigations?$select=icps_investigationid&$filter=icps_name eq {q(key)}",
                        "icps_investigationid")
            return (None, None)
    
        for t in targets:
            ent = (t.entity or "").lower() ## error here
            key = (t.ticket_number or "").strip()

            if not ent or not key:
                self.log("⚠️ Target without 'entity' or 'ticket_number' — ignored.")
                t.object_id = None
                continue

            endpoint, id_field = _build_endpoint_and_id_field(ent, key)
            if not endpoint:
                self.log(f"⚠️ Unknown entity '{ent}' — ignored.")
                t.object_id = None
                continue

            try:
                self.log(f"🔎 DV query: {endpoint}")
                result = self.dv_call(endpoint) or {}
                items = result.get("value") or []
                if items:
                    first = items[0]
                    t.object_id = first.get(id_field) or (first.get(id_field.lower()) if id_field else None)
                    self.log(f"   ✓ {ent} {key} → {t.object_id}")
                else:
                    t.object_id = None
                    self.log(f"   ⚠️ {ent} {key}: without results.")
            except Exception as e:
                t.object_id = None
                self.log(f"   ❌ Error DV ({ent} {key}): {e}")

        return targets
    
    # 2) get relative_urls por object_id
    def resolve_relative_urls(self, targets: List[Target]) -> List[Target]:
        if not self.relurl_resolver:
            raise RuntimeError("No relurl_resolver set to ObjectIdResolver.")

        for t in targets:
            try:
                if not t.object_id:
                    self.log(f"⋯ {t.entity} {t.ticket_number}: without object_id — I skip resolving relative_urls.")
                    t.relative_urls = t.relative_urls or []
                    continue
                # Only solve if they are not empty
                if not t.relative_urls:
                    urls = self.relurl_resolver(t.object_id) or []
                    t.relative_urls = self._dedupe_keep_order(urls)
            except Exception as e:
                self.log(f"❌ Error get_relativeurls_for_object_id ({t.entity} {t.ticket_number}): {e}")
                t.relative_urls = t.relative_urls or []
        return targets
    
    # 3) build sharepoint_urls por relative_urls + entidad propia
    def build_sharepoint_urls(self, targets: List[Target]) -> List[Target]:
        """
        For each Target, convert relative_urls -> sharepoint_urls using the entity itself (case -> incident, etc.). 
        Deduplicate and maintain the order of appearance.
        """
        if not self.sp_url_builder:
            raise RuntimeError("No sp_url_builder is configured in ObjectIdResolver.")
        
        # ensure we have object_id by ticket_number
        self.resolve_object_ids(targets)
        # ensure we have relative_urls by object_id
        self.resolve_relative_urls(targets)
        
        for t in targets:
            if not t.relative_urls:
                t.sharepoint_urls = []
                continue
            sp_urls: list[str] = []
            for rel in t.relative_urls:
                try:
                    url = self.sp_url_builder(rel, t.entity)
                    if url not in sp_urls:
                        sp_urls.append(url)
                except Exception as e:
                    self.log(f"⚠️ build_sharepoint_folder_url error ({t.ticket_number}, '{rel}'): {e}")
            t.sharepoint_urls = sp_urls
        return targets
    
    # 4) download sharepoint urls
    def download_sharepoint_documents(
        self,
        targets: List[Target],
        ensure_urls: bool = True,
        stop_on_error: bool = False,
        unzip_after: bool = True,
        separate_excel: bool = False
    ) -> None:
        """
        Download the content of each URL in sharepoint_urls using sp_downloader(url, ticket_number).
        - ensure_urls=True: Ensures relative_urls and sharepoint_urls first.
        - stop_on_error=False: Continues even if there are errors (logs each one).
        - unzip_after=True: After all downloads, extract 'Related Documents.zip' and remove it.
        """
        if ensure_urls:
            self.build_sharepoint_urls(targets)
            
        processed_tickets: set[str] = set()

        # Master List for combined metadata
        all_combined_metadata: List[Dict] = [] 

        for t in targets:
            if not t.object_id:
                self.log(f"⋯ {t.entity} {t.ticket_number}: without object_id — skip download.")
                continue
            if not t.sharepoint_urls:
                self.log(f"⋯ {t.entity} {t.ticket_number}: no sharepoint_urls — nothing to download.")
                continue

            for url in t.sharepoint_urls:
                try:
                    self.log(f"↓ Downloading: {t.entity} {t.ticket_number} ← {url}")
                    metadata_result = self.sp_downloader(url, t.ticket_number, separate_excel)
                    
                    if metadata_result:
                        all_combined_metadata.extend(metadata_result)
                    
                    processed_tickets.add(t.ticket_number)
                except Exception as e:
                    self.log(f"❌ Error downloading ({t.entity} {t.ticket_number}): {e}")
                    if stop_on_error:
                        raise
                    
        # --- Save Combined Excel if separate_excel is False ---
        if not separate_excel and all_combined_metadata:
            try:
                output_folder = "downloads" # O puedes usar "downloads"
                os.makedirs(output_folder, exist_ok=True)
                
                combined_path = os.path.join(output_folder, "Global_SharePoint_Metadata.xlsx")
                
                self.log(f"📊 Saving combined metadata to {combined_path}...")
                save_metadata_to_excel(all_combined_metadata, combined_path)
                
            except Exception as e:
                self.log(f"❌ Error saving combined Excel: {e}")
                    
        # --- Post-process: unzip and delete ZIP ---
        if unzip_after and processed_tickets:
            for ticket in sorted(processed_tickets):
                try:
                    if extract_related_zip(ticket, remove_zip=True):
                        self.log(f"📦 Extracted and cleaned ZIP for {ticket}")
                    else:
                        self.log(f"⋯ No ZIP found to extract for {ticket}")
                except Exception as e:
                    self.log(f"❌ Error unzipping for {ticket}: {e}")
                        
    # 5) download timeline attachments for accounts
    def get_timeline_attachments(self, targets):
        svc = TimelineAttachmentsService()
        total_notes = total_emails = 0

        for t in targets:
            if not t.object_id or not t.ticket_number:
                self.log(f"-- {t.entity} {t.ticket_number}: missing ids for timeline.")
                continue

            counts = svc.download_into_ticket_folder(
                record_id=t.object_id,
                ticket_number=t.ticket_number
            )
            total_notes  += counts["notes"]
            total_emails += counts["emails"]

        self.log(f"notes: {total_notes}, emails: {total_emails}")