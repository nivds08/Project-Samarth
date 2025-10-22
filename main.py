# src/main.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from data_handler.fetch_manager import get_dataset
from data_handler.preprocessor import preprocess
from query_engine.executor import compare_states

def main():
    # 1️⃣ Load rainfall dataset
    rainfall_df = get_dataset("rainfall")
    if rainfall_df is None:
        print("[ERROR] Rainfall dataset not found. Exiting.")
        return

    # 2️⃣ Preprocess it
    rainfall_df = preprocess(rainfall_df, "rainfall")

    # 3️⃣ Run queries
    # Compare Maharashtra vs Karnataka (all years)
    result_all_years = compare_states(rainfall_df, "Maharashtra", "Karnataka")
    print("\n=== Comparison: All Years ===")
    print(result_all_years)

    # Compare Maharashtra vs Karnataka for a specific year
    result_2022 = compare_states(rainfall_df, "Maharashtra", "Karnataka", year=2022)
    print("\n=== Comparison: Year 2022 ===")
    print(result_2022)

if __name__ == "__main__":
    main()
