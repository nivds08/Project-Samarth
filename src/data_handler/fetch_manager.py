# src/data_handler/fetch_manager.py
import os
import requests
import pandas as pd
from dotenv import load_dotenv

from .preprocessor import suggest_columns

load_dotenv()
API_KEY = os.getenv("API_KEY")


def fetch_from_api(resource_id):
    """
    Fetch data from data.gov.in API using resource ID.
    Returns a tuple: (DataFrame, column suggestions)
    """
    url = f"https://data.gov.in/api/datastore/resource.json?resource_id={resource_id}&limit=5000&apikey={API_KEY}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        records = response.json().get("records", [])
        df = pd.DataFrame(records)

        if df.empty:
            print("[WARN] API returned no records")
            return pd.DataFrame(), {}

        # Generate column suggestions
        col_suggestions = suggest_columns(df)

        return df, col_suggestions

    except Exception as e:
        print(f"[ERROR] API fetch failed for {resource_id}: {e}")
        return pd.DataFrame(), {}
