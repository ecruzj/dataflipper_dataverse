import os
import pandas as pd
from openpyxl import load_workbook

def is_valid_sheet(df):
    """
    Returns True if the sheet contains at least one named column and non-empty data.
    """
    if df is None or df.empty:
        return False

    # Remove columns that are entirely NaN
    df = df.dropna(axis=1, how="all")

    # Check if all column names are 'Unnamed' or empty
    if all(str(col).startswith("Unnamed") or str(col).strip() == "" for col in df.columns):
        return False

    # Drop rows that are all NaN
    df = df.dropna(how="all")
    
    return not df.empty and len(df.columns) > 0

def get_visible_sheets(file_path):
    """
    Uses openpyxl to get a list of visible (non-hidden) sheet names.
    """
    visible_sheets = []
    try:
        wb = load_workbook(file_path, read_only=True, data_only=True)
        for sheet in wb.worksheets:
            if sheet.sheet_state == "visible":
                visible_sheets.append(sheet.title)
        wb.close()
    except Exception:
        pass
    return visible_sheets

def read_excel_files(folder_path):
    """
    Reads all Excel files from the given folder in alphabetical order.

    Args:
        folder_path (str): Path to the folder containing Excel files.

    Returns:
        list of tuple: Each item contains (filename, {sheet_name: DataFrame}).
    """
    dataframes = []

    # Get and sort valid files alphabetically
    filenames = sorted([
        f for f in os.listdir(folder_path)
        if (f.endswith(".xlsx") or f.endswith(".xls") or f.endswith(".csv")) and not f.startswith("~$")
    ], key=str.lower)

    for filename in filenames:
        full_path = os.path.join(folder_path, filename)
        try:
            visible_sheets = get_visible_sheets(full_path)
            sheets_dict = {}

            for sheet_name in visible_sheets:
                try:
                    df = pd.read_excel(full_path, sheet_name=sheet_name, engine="openpyxl")
                    if is_valid_sheet(df):
                        sheets_dict[sheet_name] = df
                except Exception:
                    continue  # Ignore unreadable sheets

            dataframes.append((filename, sheets_dict))

        except Exception as e:
            dataframes.append((filename, {"Error": pd.DataFrame({"Exception": [str(e)]})}))

    return dataframes