# src/utils/config.py
import os
from dotenv import load_dotenv

# Explicitly provide path to .env
from pathlib import Path
env_path = Path(__file__).parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("API_KEY")
if API_KEY is None:
    raise ValueError(f"API_KEY not found! Checked at {env_path}")
