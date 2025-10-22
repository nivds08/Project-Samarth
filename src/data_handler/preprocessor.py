# src/data_handler/preprocessor.py
import pandas as pd

def suggest_columns(df, top_n=10):
    """
    Analyze the dataset and suggest potential important columns.
    Returns a dict with summary info about each column.
    """
    if df is None or df.empty:
        return {}

    col_summary = {}
    for col in df.columns:
        col_summary[col] = {
            "dtype": str(df[col].dtype),
            "num_unique": df[col].nunique(),
            "num_missing": df[col].isna().sum(),
            "sample_values": df[col].dropna().unique()[:top_n].tolist()
        }
    return col_summary
