# src/data_handler/api_handler.py
import requests
import pandas as pd
from src.utils.config import API_KEY

def fetch_data(resource_id):
    import requests
    import pandas as pd
    from src.utils.config import API_KEY

    url = "https://api.data.gov.in/resource/" + resource_id
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 1000
    }

    print(f"[DEBUG] Requesting URL: {url}")
    print(f"[DEBUG] Params: {params}")

    response = requests.get(url, params=params, timeout=60)
    print(f"[DEBUG] Response Status Code: {response.status_code}")

    if response.status_code != 200:
        print(f"[ERROR] Non-200 status: {response.text[:500]}")
        return None

    data = response.json()
    if "records" not in data:
        print("[ERROR] 'records' key not found in response JSON")
        print(data)
        return None

    df = pd.DataFrame(data["records"])
    print(f"[DEBUG] Data fetched successfully. Shape: {df.shape}")
    return df
