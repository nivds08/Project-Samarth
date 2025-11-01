# src/query_engine/executor.py
import pandas as pd

def compare_states(df1, df2, category_col=None, metric_col=None):
    """
    Compare two datasets on the specified category and metric columns.
    Returns a summary DataFrame with comparison metrics.
    
    Parameters:
        df1, df2: pandas DataFrames to compare
        category_col: column representing states/regions/categories
        metric_col: numeric column to compare (rainfall, production, etc.)
    """
    if df1 is None or df1.empty or df2 is None or df2.empty:
        print("[WARN] One of the DataFrames is empty.")
        return pd.DataFrame()

    # If columns not specified, try to guess
    if category_col is None:
        category_col = df1.columns[0]  # fallback to first column
    if metric_col is None:
        numeric_cols = df1.select_dtypes(include='number').columns
        metric_col = numeric_cols[0] if len(numeric_cols) > 0 else df1.columns[1]

    # Ensure columns exist in both datasets
    if category_col not in df1.columns or category_col not in df2.columns:
        raise ValueError(f"Category column '{category_col}' not found in both datasets")
    if metric_col not in df1.columns or metric_col not in df2.columns:
        raise ValueError(f"Metric column '{metric_col}' not found in both datasets")

    # Group by category and sum metric
    agg1 = df1.groupby(category_col)[metric_col].sum().reset_index()
    agg2 = df2.groupby(category_col)[metric_col].sum().reset_index()

    # Merge for comparison
    merged = pd.merge(agg1, agg2, on=category_col, how='outer', suffixes=('_1', '_2'))
    merged.fillna(0, inplace=True)

    # Compute difference and percentage change
    merged['difference'] = merged[f'{metric_col}_2'] - merged[f'{metric_col}_1']
    merged['pct_change'] = merged['difference'] / merged[f'{metric_col}_1'].replace(0, 1) * 100

    return merged
