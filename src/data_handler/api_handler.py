import requests
import pandas as pd
from src.utils.config import API_KEY

def fetch_data(resource_id, filters=None, limit=100):
    """
    Fetch data from data.gov.in API by resource_id, with optional filters.
    Returns a DataFrame.
    """
    base_url = f"https://api.data.gov.in/resource/{resource_id}"
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": limit
    }

    # Add filters if provided
    if filters:
        for key, value in filters.items():
            params[f"filters[{key}]"] = value

    try:
        response = requests.get(base_url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if "records" in data and len(data["records"]) > 0:
            return pd.DataFrame(data["records"])
        else:
            print("⚠️ No records found for given filters.")
            return pd.DataFrame()
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")
        return pd.DataFrame()
