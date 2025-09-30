import pandas as pd
from core.services.dataverse_client import call_dataverse

INPUT_FILE = "data/Merge_Accounts_ICPS - format.xlsx"
COLUMN_NAME = "BUS ID"

def get_column_name():
    return COLUMN_NAME

def get_account_id_by_bus_id(bus_id: str) -> str | None:
    endpoint = f"accounts?$filter=accountnumber eq '{bus_id}'&$select=accountid"
    result = call_dataverse(endpoint)
    
    records = result.get("value", [])
    if records:
        return records[0].get("accountid")
    return None

def fetch_accounts_from_ICPS() -> pd.DataFrame:
    endpoint = "accounts"
    records = []

    while endpoint:
        result = call_dataverse(endpoint)
        batch = result.get("value", [])
        records.extend(batch)
        endpoint = result.get("@odata.nextLink")
        
        # Remove the full URL if `call_dataverse()` only accepts the relative path
        if endpoint and endpoint.startswith("https://"):
            endpoint = endpoint.split("/api/data/v9.2/")[-1]
            
    df = pd.DataFrame(records)
    df.to_excel("ICPS_Accounts.xlsx", index=False)

    return records

def fetch_accounts() -> pd.DataFrame:
    df = pd.read_excel(INPUT_FILE)

    if COLUMN_NAME not in df.columns:
        raise Exception(f"❌ The column '{COLUMN_NAME}' doesn't exist in the Excel file.")

    df["accountid"] = df[COLUMN_NAME].apply(lambda bus_id: get_account_id_by_bus_id(bus_id))
    return df

def main():
    
    """
    Main function to read an Excel file, fetch account IDs for each Business ID,
    and output the results to a new Excel file.

    The function performs the following steps:
    1. Reads the input Excel file specified by INPUT_FILE.
    2. Checks if the specified column, COLUMN_NAME, exists in the DataFrame.
       Raises an exception if the column is not found.
    3. Initializes a new column, 'accountid', in the DataFrame to store results.
    4. Iterates over each row in the DataFrame, retrieves the Business ID, and
       fetches the corresponding account ID using the get_account_id_by_bus_id function.
    5. Stores the fetched account ID in the 'accountid' column, and prints the progress.
    6. Exports the DataFrame with the results to an Excel file.
    """

    df = pd.read_excel(INPUT_FILE)

    if COLUMN_NAME not in df.columns:
        raise Exception(f"❌ The column '{COLUMN_NAME}' doesn't exist in the Excel file. Make sure the column existe in the file..")

    # New column to store results
    df["accountid"] = None

    for index, row in df.iterrows():
        bus_id = row[COLUMN_NAME]
        print(f"🔍 Searching accountid for BUS ID: {bus_id}...")
        account_id = get_account_id_by_bus_id(bus_id)
        df.at[index, "accountid"] = account_id
        print(f"✅ Result: {account_id or 'Not found'}")

    # Export results
    output_file = "data/accounts_with_ids.xlsx"
    df.to_excel(output_file, index=False)
    print(f"\n📁 File generated with results: {output_file}")

if __name__ == "__main__":
    main()