# src/data_handler/fetch_manager.py
import os
import sys
import pandas as pd
import requests

# Ensure src is in path (needed for Streamlit)
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import local modules


from src.data_handler.preprocessor import suggest_columns
from src.data_handler.api_handler import fetch_data

def fetch_from_api(resource_id):
    """
    Fetch dataset from data.gov.in using resource_id and suggest columns.
    Returns: DataFrame, suggestions
    """
    df = fetch_data(resource_id)
    if df is not None and not df.empty:
        suggestions = suggest_columns(df)
        return df, suggestions
    return df, {}
