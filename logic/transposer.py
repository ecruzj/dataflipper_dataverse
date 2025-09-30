import pandas as pd

def transpose_row_by_row(df):
    """
    Transposes each row of the DataFrame so that columns become vertical entries per record.
    Filters out unwanted internal columns.

    Args:
        df (pd.DataFrame): The original DataFrame.

    Returns:
        list of list of dict: Each inner list contains dicts with 'Field' and 'Value'.
    """
    # Remove completely empty columns and rows
    df = df.dropna(axis=1, how="all").dropna(how="all")

    # Columns to exclude
    exclude_keywords = ["(Do Not Modify)"]

    # Filter out unwanted columns
    df = df[[col for col in df.columns if not any(kw in str(col) for kw in exclude_keywords)]]

    # Transpose each row individually
    transposed_data = []
    try:
        for _, row in df.iterrows():
            transposed_record = []
            for col, val in row.items():
                display_val = '-None' if pd.isna(val) else str(val) # Replace NaN with '-None'
                transposed_record.append((str(col), display_val))
            transposed_data.append(transposed_record)
        return transposed_data
    except Exception as e:
        raise Exception(f"Error transposing row: {str(e)}")
    
    # try:
    #     for _, row in df.iterrows():
    #         transposed_record = []
    #         for col in df.columns:
    #             transposed_record.append({
    #                 "Field": str(col),
    #                 "Value": str(row[col])
    #             })
    #         transposed_data.append(transposed_record)
    #     return transposed_data
    # except Exception as e:
    #     raise Exception(f"Error transposing row: {str(e)}")