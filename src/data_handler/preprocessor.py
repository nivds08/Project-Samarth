# src/data_handler/preprocessor.py
import pandas as pd

def preprocess(df, dataset_type):
    """
    Basic preprocessing for different dataset types.
    Currently supports: 'rainfall'
    """
    if df is None or df.empty:
        print("[WARN] Empty DataFrame passed to preprocess")
        return df

    if dataset_type.lower() == "rainfall":
        # Ensure columns are correct
        df = df.rename(columns=str.lower)
        # Example: standardize state names
        if "state" in df.columns:
            df["state"] = df["state"].str.strip().str.title()
        # Ensure year column is integer
        if "year" in df.columns:
            df["year"] = df["year"].astype(int)
        # Ensure rainfall column exists
        if "rainfall_mm" in df.columns:
            df["rainfall_mm"] = pd.to_numeric(df["rainfall_mm"], errors="coerce")
    return df
