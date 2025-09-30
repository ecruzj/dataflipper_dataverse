import os
import json
import sys
from pathlib import Path
from typing import Any, Mapping
import pandas as pd

from dataverse_apis.core.services.runtime_paths import resolve_runtime_path

def export_targets_to_excel(targets: Any,
                            output_path: str | os.PathLike,
                            entity_columns: list[str] | None = None) -> str:
    """
    Exports 'targets' to an Excel file.
    - targets can be: DataFrame, list[dict], list[Any], dict[str, list[dict] | DataFrame]
    * If it's a dict => creates a workbook with one sheet per key.
    * If it's a list[dict] or DataFrame => a single sheet named 'targets'.
    - entity_columns: preferred column order (non-existent columns are ignored).

    Returns the entered path.
    """

    def _normalize_cell(v):
        # Serializes complex structures so they don't break when writing
        if isinstance(v, (dict, list, tuple, set)):
            try:
                return json.dumps(v, ensure_ascii=False)
            except Exception:
                return str(v)
        return v

    def _to_df(obj: Any) -> pd.DataFrame:
        if isinstance(obj, pd.DataFrame):
            return obj.copy()
        if isinstance(obj, list):
            if len(obj) == 0:
                return pd.DataFrame(columns=entity_columns or [])
            if isinstance(obj[0], Mapping):
                return pd.DataFrame([{k: _normalize_cell(v) for k, v in row.items()} for row in obj])
            # simple list
            return pd.DataFrame({"value": [_normalize_cell(x) for x in obj]})
        # climb or something weird
        return pd.DataFrame({"value": [_normalize_cell(obj)]})

    def _reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
        if not entity_columns:
            return df
        first = [c for c in entity_columns if c in df.columns]
        rest  = [c for c in df.columns if c not in first]
        return df[first + rest]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Multi-sheet case: dict with collections by key
    if isinstance(targets, Mapping):
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for sheet_name, data in targets.items():
                df = _reorder_columns(_to_df(data))
                # Excel does not allow names >31 or certain characters
                safe_name = str(sheet_name)[:31].replace(":", "_").replace("/", "_").replace("\\", "_").replace("*", "_").replace("?", "_").replace("[", "_").replace("]", "_")
                if df.empty:
                    # we ensure at least one column to create the sheet
                    df = pd.DataFrame({"_empty": []})
                df.to_excel(writer, sheet_name=safe_name or "Sheet", index=False)
    else:
        # Single-leaf case
        df = _reorder_columns(_to_df(targets))
        df.to_excel(output_path, index=False)

    return str(output_path)

def collect_targets_from_excels(self, excel_files, entity_columns: dict[str, str]) -> list[dict]:
        """
        It loops through each Excel file and, if its first word matches a known entity,
        searches its sheets for the configured column and collects *all* non-empty ticket_numbers.
        Returns a list unique by ticket_number (globally).
        """
        
        def _first_word(text: str) -> str:
        # "eCase Advanced Find View..." -> "eCase"
            return text.split()[0] if text else ""
    
        def _find_column_case_insensitive(columns, target_name: str) -> str | None:
                """
                Returns the actual name of the column in the DF that matches (case/spaces) target_name.
                """
                target = target_name.strip().lower()
                normalized = {str(c).strip().lower(): str(c) for c in columns}
                return normalized.get(target)
        
        # ticket_normalized -> target
        targets_by_ticket: dict[str, dict] = {}

        def _norm_ticket(v: str) -> str:
            # normalizer for comparison (avoids duplicates with case/space variations)
            return str(v).strip().upper()

        for filename, sheets in excel_files:
            entity_key = _first_word(Path(filename).stem).lower()
            if entity_key not in entity_columns:
                continue

            target_col_cfg = entity_columns[entity_key]  # expected column name

            for sheet_name, df in sheets.items():
                col_actual = _find_column_case_insensitive(df.columns, target_col_cfg)
                if not col_actual:
                    continue

                # all non-empty tickets in the column
                series = df[col_actual].dropna().astype(str).str.strip()
                series = series[series != ""]

                # We iterate while preserving order; we avoid duplicates per ticket.
                seen_local = set()
                for ticket in series:
                    norm = _norm_ticket(ticket)
                    if not norm or norm in seen_local:
                        continue
                    seen_local.add(norm)

                    if norm in targets_by_ticket:
                        prev = targets_by_ticket[norm]
                        if prev["entity"] != entity_key:
                            # Conflict: same ticket in another entity → we keep the first one and notify
                            self.log_updated.emit(
                                f"⚠️ Ticket '{ticket}' already registered for entity '{prev['entity']}'. "
                                f"I ignore duplicate in '{entity_key}' (file: {filename}, sheet: {sheet_name})."
                            )
                        # If it is the same entity, we simply ignore the duplicate.
                        continue

                    # Register the target
                    targets_by_ticket[norm] = {
                        "entity": entity_key,
                        "ticket_number": str(ticket),
                        "file": filename,
                        "sheet": sheet_name,
                        "column": col_actual,
                    }

        return list(targets_by_ticket.values())
    
def load_entity_columns_map(self) -> dict[str, str]:
        """
        Reads Excel and returns: {entity_lower: column_name_str}
        Only includes rows where 'Sharepoint Doc' is 'Y'.
        """    
        path = resolve_runtime_path(Path("resources") / "entity_mapping.xlsx")
        
        if not path:
            self.log_updated.emit("⚠️ entity_mapping.xlsx not found; SharePoint flow will not be applied.")
            return {}

        try:
            df = pd.read_excel(path)  # requires openpyxl
        except Exception as e:
            self.log_updated.emit(f"❌ The mapping could not be read '{path}': {e}")
            return {}

        # we normalize column names
        cols = {str(c).strip().lower(): str(c) for c in df.columns}
        def pick(*cands):
            for c in cands:
                key = c.strip().lower()
                if key in cols:
                    return cols[key]
            return None

        col_entity = pick("entity")
        col_spdoc = pick("sharepoint doc", "sharepoint_doc", "spdoc", "sp doc")
        col_colname = pick("column name", "column", "column_name")

        if not (col_entity and col_spdoc and col_colname):
            self.log_updated.emit("❌ The mapping does not contain expected columns: 'Entity', 'Sharepoint Doc', 'Column Name'.")
            return {}

        mapping: dict[str, str] = {}
        for _, row in df.iterrows():
            spdoc = str(row.get(col_spdoc, "")).strip().lower()
            if not spdoc.startswith("y"):
                continue  # solo filas marcadas con Y
            entity = str(row.get(col_entity, "")).strip().lower()
            colname = str(row.get(col_colname, "")).strip()
            if entity and colname:
                mapping[entity] = colname

        if not mapping:
            self.log_updated.emit(f"⚠️ Empty mapping in '{path}'.")
            return {}

        self.log_updated.emit(f"✅ Feature mapping loaded ({len(mapping)}): {path}")
        return mapping
