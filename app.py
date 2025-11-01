import sys
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# --- Setup paths ---
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.data_handler.fetch_manager import fetch_from_api
from src.query_engine.executor import compare_states  # keep as-is

load_dotenv()

# --- Dataset mapping ---
DATASETS = {
    "All India Rainfall (1901-2015)": "8196f6cc-83ff-4b56-8581-2630de9d4a5e",
    "Sub-Divisional Rainfall (1901-2017)": "722e2530-dcb1-4104-bd8f-5a0b22e68999",
    "District Crop Production (1997)": "35be999b-0208-4354-b557-f6ca9a5355de",
    "Sub-division rainfall": "8e0bd482-4aba-4d99-9cb9-ff124f6f1c2f",
    "Max/Min Temp-rainfall": "6df1ecaa-5ebe-477d-9ffe-4e1b87dd71e3",
    "District-rainfall": "d0419b03-b41b-4226-b48b-0bc92bf139f8",
    "Rainfall-Central India": "40e1b431-eae6-4ab2-8587-b8ddbdd6bf1c",
    "Different-Crops(2019)": "f20d7d45-e3d8-4603-bc79-15a3d0db1f9a",
    "Area_production": "62bdce72-56c6-4d12-b875-27aff49275e3",
    "Principal Crops": "e540df91-65d2-45a1-8b2d-b4f11023a042",
    "Paddy-crop arrival": "1ec5d89e-6cff-4358-958c-67432e7a73f9",
    "Vegetable production": "1e82c76f-ba78-4492-9799-2f6bc05430fe",
    "Vegetable-crops": "d6e5315d-d4a7-4f1f-ab23-c2adcac3e1e7"
}

st.set_page_config(page_title="Data Portal Viewer", layout="wide")
st.title("📊 Data Portal Viewer")

# --- Dataset selection ---
selected_dataset = st.selectbox("Choose a dataset:", list(DATASETS.keys()))

# --- Button to fetch ---
if st.button("Fetch Data", key="fetch_btn"):
    resource_id = DATASETS[selected_dataset]
    with st.spinner(f"Fetching data for **{selected_dataset}**..."):
        df, col_suggestions = fetch_from_api(resource_id)

    if df is not None and not df.empty:
        st.success(f"✅ Successfully fetched {len(df)} records!")

        # --- Column suggestions ---
        st.markdown("### 🔹 Column Suggestions")
        if isinstance(col_suggestions, dict) and len(col_suggestions) > 0:
            for col, info in col_suggestions.items():
                st.write(f"**{col}** — dtype: {info['dtype']}, unique: {info['num_unique']}, missing: {info['num_missing']}")
                st.caption(f"Sample: {info['sample_values']}")
        else:
            st.warning("⚠️ Column suggestions are not available for this dataset.")

        # --- Query-based filtering ---
        st.markdown("### 🧠 Ask a question about this dataset")
        user_query = st.text_input("Example: 'rainfall in Kerala 2010' or 'production of paddy in Punjab'")

        def extract_filters_from_query(query, df):
            query = query.lower()
            filters = {}
            for col in df.columns:
                for val in df[col].astype(str).unique():
                    val_str = str(val).lower()
                    if len(val_str) > 2 and val_str in query:
                        filters[col] = val
                        break
            return filters

        filtered_df = df.copy()
        if user_query:
            filters = extract_filters_from_query(user_query, df)
            if filters:
                st.info(f"Detected filters: {filters}")
                for col, val in filters.items():
                    filtered_df = filtered_df[filtered_df[col].astype(str).str.lower() == str(val).lower()]
            else:
                st.warning("Could not detect any matching keywords from your query. Try again.")

        # --- Display filtered data ---
        st.markdown("### 🔹 Filtered Data")
        if not filtered_df.empty:
            st.dataframe(filtered_df)
        else:
            st.warning("No matching records found for the given filters.")

        # --- Optional manual filtering ---
        st.markdown("### ⚙️ Manual Filters (Optional)")
        for col in df.columns:
            if df[col].dtype == "object" or df[col].nunique() <= 20:
                options = df[col].dropna().unique().tolist()
                selected_vals = st.multiselect(f"Filter {col}", options, default=options)
                filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]
            elif pd.api.types.is_numeric_dtype(df[col]):
                min_val, max_val = float(df[col].min()), float(df[col].max())
                selected_range = st.slider(f"Filter {col}", min_val, max_val, (min_val, max_val))
                filtered_df = filtered_df[(filtered_df[col] >= selected_range[0]) & (filtered_df[col] <= selected_range[1])]

        st.dataframe(filtered_df)

        # --- Download filtered data ---
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Filtered Data
