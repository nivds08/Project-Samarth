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
    from src.data_handler.api_handler import fetch_data
    import pandas as pd

    try:
        df = fetch_data(resource_id)
        if df is not None and not df.empty:
            column_suggestions = list(df.columns)
            return df, column_suggestions
        else:
            return None, []
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return None, []
