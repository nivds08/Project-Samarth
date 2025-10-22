import pandas as pd
import os
from dotenv import load_dotenv
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

def get_dataset(name):
    """
    Load dataset by name.
    Currently supports: 'rainfall'
    """
    if name.lower() == "rainfall":
        path = os.path.join(DATA_DIR, "rainfall.csv")
        if os.path.exists(path):
            return pd.read_csv(path)
        else:
            print(f"[ERROR] {path} does not exist")
            return None
    else:
        print(f"[WARN] No dataset found for {name}")
        return None
