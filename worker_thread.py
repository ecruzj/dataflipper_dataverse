import os
from pathlib import Path
import pandas as pd
from PySide6.QtCore import QThread, Signal
from logic.data_frame_helper import collect_targets_from_excels, export_targets_to_excel, load_entity_columns_map
from logic.file_reader import read_excel_files
from logic.transposer import transpose_row_by_row
from logic.pdf_generator import (
    generate_pdf,
    generate_combined_pdf,
    generate_pdf_per_excel,
)
from logic.related_documents_service import RelatedDocumentsService, to_targets, to_dicts

# --- DEFINITION OF WEIGHTS (COSTS) ---
# COST_PREPARE_TARGET = 1     # cost by identifying a target
COST_BUILD_URL = 1          # Local logic (fast)
COST_RESOLVE_ID = 5         # Call to Dataverse to resolve ID
COST_RESOLVE_URL = 5        # Call to Dataverse to resolve relative URL
COST_TIMELINE = 20          # cost by timeline attachments
COST_TRANSPOSE_SHEET = 50   # cost by excel sheet transposed
COST_FINAL_EXPORT = 50      # cost by generating PDF/Excel final
COST_DOWNLOAD_SP = 100      # cost by downloading full (Nav+Meta+DL)

class WorkerThread(QThread):
    progress_updated = Signal(int)
    log_updated = Signal(str)
    log_pdf_update = Signal(str)
    finished = Signal(bool, list)  # success, error_list

    def __init__(self, folder_path: str, export_mode: str, process_type: str):
        """
        Constructor for WorkerThread.

        :param folder_path: Path to the folder containing Excel files
        :param export_mode: The export mode to use. Can be "per_sheet",
            "per_excel" or "combined".
        """
        super().__init__()
        self.folder_path = folder_path
        self.export_mode = export_mode    # "separate", "per_excel", "combined"
        self.process_type = process_type  # "transpose_only", "transpose_and_docs", "docs_only"
        self.output_dir = "output"
        self.errors: list[str] = []
        
        # status of progress
        self._p_total = 1
        self._p_done = 0
        
    # ----------------------------- Driver -----------------------------
    def run(self):
        ok = True
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 1. Read Excel files
            excel_files = self._read_excel_files()
            
            # 2. estimate total steps
            total_sheets = sum(len(sheets) for _, sheets in excel_files)
            total_tickets = 0
            targets_precalculed = []
            
            if self._should_get_docs():
                entity_columns = load_entity_columns_map(self)
                if entity_columns:
                    # this function is fast, it only reads cells in memory
                    targets_precalculed = collect_targets_from_excels(self, excel_files, entity_columns)
                    total_tickets = len(targets_precalculed)
                    
            # 3 calculate total points
            total_points = 0
            
            if self._should_transpose():
                total_points += (total_sheets * COST_TRANSPOSE_SHEET)
                total_points += COST_FINAL_EXPORT # Generate combined PDF / per-excel PDFs
                
            if self._should_get_docs():
                total_points += (total_tickets * COST_RESOLVE_ID)
                total_points += (total_tickets * COST_RESOLVE_URL)
                total_points += (total_tickets * COST_BUILD_URL)
                total_points += (total_tickets * COST_DOWNLOAD_SP)
                total_points += (total_tickets * COST_TIMELINE)
                total_points += COST_FINAL_EXPORT # Excel targets

            # Initialize progress bar with total points
            self._p_init(total_points)
            self.log_updated.emit(f"📊 Planning: {total_sheets} Sheets, {total_tickets} Tickets. Total Points: {total_points}")
            
            # 4. Execute flows
            if self._should_transpose():
                self._transpose_flow(excel_files)

            if self._should_get_docs():
                self._related_documents_flow(targets_precalculed)


        except Exception as e:
            self._log_error("Unexpected error", e)
            ok = False
        
        # always close at 100%
        self._p_finish()
        self.finished.emit(ok and not self.errors, self.errors)
        
    # --------------------------- Option Helpers ------------------------------
    def _should_transpose(self) -> bool:
        return self.process_type in ("transpose_only", "transpose_and_docs")

    def _should_get_docs(self) -> bool:
        return self.process_type in ("transpose_and_docs", "docs_only")

    def _read_excel_files(self):
        self.log_updated.emit("📂 Reading Excel files...")
        files = read_excel_files(self.folder_path)  # [(filename, {sheet_name: df, ...}), ...]
        if not files:
            self.log_updated.emit("⚠️ No Excel files found.")
        return files

    def _log_error(self, message: str, exc: Exception):
        msg = f"❌ {message}: {exc}"
        self.log_updated.emit(msg)
        self.errors.append(msg)
        
    # --- Progress helpers -------------------------------------------------
    def _p_init(self, total_steps: int):
        # avoid division by zero
        self._p_total = max(1, int(total_steps))
        self._p_done = 0
        self.progress_updated.emit(0)

    def _p_step(self, points: int = 1):
        """Advance the bar N points"""
        self._p_done += points
        # Calculate percentage
        pct = int(min(99, (self._p_done / self._p_total) * 100))
        self.progress_updated.emit(pct)

    def _p_finish(self):
        self.progress_updated.emit(100)
        
    # ------------------------ Transpose / PDF flow --------------------
    def _transpose_flow(self, excel_files):        
        combined_data = []         # [(title, df_transposed), ...]
        excel_file_data = []       # [(filename, [(sheet, df_transposed), ...])]

        for filename, sheets in excel_files:
            file_entry = (filename, [])
            for sheet_name, df in sheets.items():
                if df.empty:
                    continue
                try:
                    self.log_updated.emit(f"📄 Processing: {filename} - Sheet: {sheet_name}")
                    transposed = transpose_row_by_row(df)
                    self._collect_export_units(filename, sheet_name, transposed, combined_data, file_entry)
                    
                    self._p_step(COST_TRANSPOSE_SHEET)  # processing + export/gluing
                    self.log_updated.emit(f"✔ Done: {filename} - {sheet_name}\n")
                except Exception as e:
                    self._log_error(f"Error in {filename} - {sheet_name}", e)

            if self.export_mode == "per_excel" and file_entry[1]:
                excel_file_data.append(file_entry)

        self._final_exports(combined_data, excel_file_data)
        self._p_step(COST_FINAL_EXPORT)  # final export step
                
    def _collect_export_units(self, filename, sheet_name, df_transposed, combined_data, file_entry):
        """Decide what to do with each sheet based on the export_mode."""
        if self.export_mode == "combined":
            title = f"{filename} - {sheet_name}"
            combined_data.append((title, df_transposed))
        elif self.export_mode == "per_excel":
            file_entry[1].append((sheet_name, df_transposed))
        else:  # "separate"
            generate_pdf(
                df_transposed,
                self.output_dir,
                filename,
                sheet_name,
                log_callback=self.log_pdf_update.emit,
            )

    def _final_exports(self, combined_data, excel_file_data):
        try:
            if self.export_mode == "combined":
                self.log_updated.emit("📄 Generating combined PDF...")
                generate_combined_pdf(combined_data, self.output_dir, log_callback=self.log_pdf_update.emit)
                self._p_step(2)  # pre + post (already mentioned above)

            elif self.export_mode == "per_excel":
                self.log_updated.emit("📁 Generating PDFs per Excel file...")
                for filename, rows in excel_file_data:
                    generate_pdf_per_excel({filename: rows}, self.output_dir, log_callback=self.log_pdf_update.emit)
                    self._p_step(1)

        except Exception as e:
            self._log_error("Final export error", e)
                        
    # ---------------------- Related documents flow ------------------------
    def _related_documents_flow(self, targets):
        """
        Builds a unique list per entity with the "ticket number" read
        from Excel files whose filename matches the entity.
        """
        if not targets:
            self.log_updated.emit("⚠️ No targets to process.")
            return

        # Instantiate service with the point stepper
        resolver = RelatedDocumentsService(
            logger=self.log_updated.emit,
            progress_stepper=self._p_step
        )
        
        targets = to_targets(targets)
        
        # 1. Build URLs and object IDs (Consume COST_PREPARE_TARGET per ticket)
        targets = resolver.build_sharepoint_urls(targets)
        
        # 2. Download documents (Consume COST_DOWNLOAD_SP per ticket)
        resolver.download_sharepoint_documents(targets, ensure_urls=False, separate_excel=False)
        
        # 3. Timeline attachments (Consume COST_TIMELINE per ticket)
        resolver.get_timeline_attachments(targets)
        
        # 4. Export Excel with targets
        outfile = "output/targets.xlsx"
        
        # 5. Export targets to Excel
        self.log_updated.emit("📄 Exporting targets to Excel...")
        # Load entity columns to export
        entity_columns = load_entity_columns_map(self) 
        if entity_columns:
            export_targets_to_excel(to_dicts(targets), outfile, list(entity_columns.keys()))
        
        self._p_step(COST_FINAL_EXPORT)  # final export step