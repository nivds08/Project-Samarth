
# src/utils/config.py
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env from project root

API_KEY = os.getenv("API_KEY")
if API_KEY is None:
    raise ValueError("API_KEY not found! Make sure .env exists in project root and contains API_KEY.")
