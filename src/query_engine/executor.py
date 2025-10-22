# src/query_engine/executor.py

import pandas as pd

def compare_states(df, state1, state2, year=None):
    """
    Compare average rainfall between two states, optionally for a specific year.
    """
    if df is None or df.empty:
        print("[WARN] DataFrame is empty.")
        return None

    df_filtered = df.copy()

    # Filter by year if provided
    if year is not None:
        df_filtered = df_filtered[df_filtered["year"] == year]

    # Filter for selected states
    df_filtered = df_filtered[df_filtered["state"].isin([state1, state2])]

    if df_filtered.empty:
        print("[WARN] No data found for the selected states/year.")
        return None

    # Group and calculate average rainfall
    comparison = (
        df_filtered.groupby("state")["rainfall_mm"]
        .mean()
        .reset_index()
        .rename(columns={"rainfall_mm": "average_rainfall_mm"})
    )

    return comparison
