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
        
    # ----------------------------- Driver -----------------------------
    def run(self):
        ok = True
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            excel_files = self._read_excel_files()

            if self._should_transpose():
                self._transpose_flow(excel_files)

            if self._should_get_docs():
                self._related_documents_flow(excel_files)

        except Exception as e:
            self._log_error("Unexpected error", e)
            ok = False

        self.finished.emit(ok and not self.errors, self.errors)
        
    # --------------------------- Helpers ------------------------------
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
                    self.log_updated.emit(f"✔ Done: {filename} - {sheet_name}\n")
                except Exception as e:
                    self._log_error(f"Error in {filename} - {sheet_name}", e)

            if self.export_mode == "per_excel" and file_entry[1]:
                excel_file_data.append(file_entry)

        self._final_exports(combined_data, excel_file_data)
                
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

            elif self.export_mode == "per_excel":
                self.log_updated.emit("📁 Generating PDFs per Excel file...")
                for filename, rows in excel_file_data:
                    generate_pdf_per_excel({filename: rows}, self.output_dir, log_callback=self.log_pdf_update.emit)

        except Exception as e:
            self._log_error("Final export error", e)
                        
    # ---------------------- Related documents flow ------------------------    
    def _related_documents_flow(self, excel_files):
        """
        Builds a unique list per entity with the "ticket number" read
        from Excel files whose filename matches the entity.
        """
        entity_columns = load_entity_columns_map(self)
        if not entity_columns:
            return

        # 1) Build targets list
        targets = collect_targets_from_excels(self, excel_files, entity_columns)
        
        if not targets:
            self.log_updated.emit("⚠️ No matching entities/tickets found para SharePoint.")
            return

        # 2) Enrich with relative+sharepoint urls
        resolver = RelatedDocumentsService(logger=self.log_updated.emit)
        targets = to_targets(targets) # dicts -> dataclasses
        # targets = resolver.enrich_with_sharepoint_urls(targets) # add object_id, relative_url, sharepoint_url        
        
        # 3) Download (the method is responsible for resolving relative+sharepoint URLs if ensure_urls=True)
        resolver.download_sharepoint_documents(targets, ensure_urls=True)
                        
        outfile = "output/targets.xlsx"  # pon tu ruta preferida
        export_targets_to_excel(to_dicts(targets), outfile, entity_columns)