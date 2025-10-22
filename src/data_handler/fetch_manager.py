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
    from src.data_handler.api_handler import fetch_data_using_resource_id
    import pandas as pd

    print(f"\n[DEBUG] Trying to fetch data for resource_id: {resource_id}")

    try:
        df = fetch_data(resource_id)
        print(f"[DEBUG] DataFrame returned: {type(df)} with shape {df.shape if isinstance(df, pd.DataFrame) else 'N/A'}")
        return df
    except Exception as e:
        print(f"[ERROR] Exception during fetch: {e}")
        return None
