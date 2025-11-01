import requests
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("API_KEY")

def fetch_from_api(resource_id, limit=1000):
    """
    Fetch data from data.gov.in API using resource_id.
    Returns a DataFrame and column suggestions.
    """
    base_url = "https://api.data.gov.in/resource/"
    url = f"{base_url}{resource_id}"
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": limit
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if "records" in data and isinstance(data["records"], list):
            df = pd.DataFrame(data["records"])

            # Build column suggestions
            col_suggestions = {}
            for col in df.columns:
                col_suggestions[col] = {
                    "dtype": str(df[col].dtype),
                    "num_unique": df[col].nunique(),
                    "num_missing": df[col].isna().sum(),
                    "sample_values": df[col].dropna().unique()[:5].tolist()
                }

            return df, col_suggestions
        else:
            return pd.DataFrame(), {}

    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame(), {}
