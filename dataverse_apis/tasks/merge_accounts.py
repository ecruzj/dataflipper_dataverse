import pandas as pd
from tqdm import tqdm
from tasks.fetch_accounts import get_column_name
from core.services.dataverse_client import call_dataverse

OUTPUT_FILE = "data/merged_output_results.xlsx"

def call_merge_endpoint(target_account_id: str, subordinate_account_id: str) -> dict:
    try:
        endpoint = "Merge"
        payload = {
            "Target": {
                "@odata.type": "Microsoft.Dynamics.CRM.account",
                "accountid": target_account_id
            },
            "Subordinate": {
                "@odata.type": "Microsoft.Dynamics.CRM.account",
                "accountid": subordinate_account_id
            },
            "PerformParentingChecks": False
        }
        return call_dataverse(endpoint, method="POST", data=payload)
    except Exception as e:
        return {"status": f"error: {str(e)}", "code": 500}

def merge_accounts(target_account: dict, subordinate_accounts: list[dict]) -> dict:
    errors = []
    details = {}

    for subordinate in tqdm(
        subordinate_accounts,
        desc=f"🔃 Merging Group {target_account['Merge_Group_ID']}",
        unit="sub",
        leave=False,
        ncols=60
    ):
        subordinate_id = subordinate.get("accountid")
        if not subordinate_id:
            details["UNKNOWN"] = "❌ Subordinate without accountid"
            errors.append("Subordinate without accountid")
            continue

        try:
            result = call_merge_endpoint(target_account["accountid"], subordinate_id)
            code = result.get("code", None)
            status = result.get("status", "unknown")

            if code == 204:
                details[subordinate_id] = f"✅ Merge successful (code: {code})"
            else:
                msg = f"❌ Merge failed (code: {code}, status: {status})"
                details[subordinate_id] = msg
                errors.append(msg)

        except Exception as e:
            msg = f"❌ Exception: {str(e)}"
            details[subordinate_id] = msg
            errors.append(msg)

    summary = "✅ All merges successful" if not errors else "❌ Merge completed with errors"

    return {
        "summary": summary,
        "details": details
    }

def process_merge_for_all_groups(df: pd.DataFrame) -> pd.DataFrame:
    df["merge_result"] = None
    df["merge_detail"] = None
    column_name = get_column_name()

    duplicates = df[df.duplicated(column_name, keep=False)]
    if not duplicates.empty:
        raise Exception(f"❌ Error: Duplicates found in '{column_name}' column:\n{duplicates[[column_name, 'Merge_Group_ID']]}")

    for group_id, group in tqdm(df.groupby("Merge_Group_ID"), desc="🔄 Processing Merge Groups", unit="group"):
        target_row = group[group["Merge_Role"] == 1]
        subordinates = group[group["Merge_Role"] == 0]

        if len(target_row) == 0:
            df.loc[group.index, "merge_result"] = "❌ Error: No Target account in group"
            df.loc[group.index, "merge_detail"] = "No Target account present"
            continue
        elif len(target_row) > 1:
            df.loc[group.index, "merge_result"] = f"❌ Error: Multiple Target accounts in group ({len(target_row)})"
            df.loc[group.index, "merge_detail"] = "Multiple Target accounts detected"
            continue
        elif len(subordinates) == 0:
            df.loc[group.index, "merge_result"] = "❌ Error: No Subordinate in group"
            df.loc[group.index, "merge_detail"] = "No Subordinate present"
            continue

        target_account = target_row.iloc[0].to_dict()
        subordinate_accounts = subordinates.to_dict(orient="records")

        print("\n" + "-"*60)
        print(f"🔧 Merge Group: {group_id}")
        print(f"📌 Target Account ID: {target_account['accountid']}")
        print(f"   ↳ Subordinate(s): {[s['accountid'] for s in subordinate_accounts]}")

        merge_output = merge_accounts(target_account, subordinate_accounts)

        df.loc[group.index, "merge_result"] = merge_output["summary"]

        for idx, row in group.iterrows():
            account_id = row.get("accountid")
            detail = merge_output["details"].get(
                account_id,
                "✅ Main account (no action)" if row["Merge_Role"] == 1 else "⚠️ No detail"
            )
            df.at[idx, "merge_detail"] = detail

    df.to_excel(OUTPUT_FILE, index=False)
    print(f"\n📁 Generated file: {OUTPUT_FILE}")

    return df