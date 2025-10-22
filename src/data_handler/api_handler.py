# src/data_handler/api_handler.py
import requests
import pandas as pd
from src.utils.config import API_KEY

def fetch_data(api_url, params=None):
    """
    Fetch data from API and return as DataFrame.
    """
    if params is None:
        params = {}
    params['apikey'] = API_KEY

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data.get('records', []))
        if df.empty:
            print("[WARN] API returned no records")
            return None
        return df
    except Exception as e:
        print(f"[ERROR] API request failed: {e}")
        return None
