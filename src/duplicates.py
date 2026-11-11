

def find_duplicates(df, subset=None):
    """
    Find duplicate rows in a DataFrame.

    Args:
        df: Input pandas DataFrame.
        subset: Columns to check for duplicates.
               If None, all columns are checked.

    Returns:
        DataFrame containing duplicate rows.
    """

    if df.empty:
        return df.copy()

    duplicate_rows = df[df.duplicated(subset=subset, keep="first")]

    return duplicate_rows
