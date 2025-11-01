import sys
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# --- setup paths so `src` imports work ---
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.data_handler.fetch_manager import fetch_from_api
from src.query_engine.executor import compare_states

load_dotenv()

# --- dataset mapping ---
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
st.markdown(
    """
    <style>
    div[data-baseweb="select"] > div {
        cursor: pointer !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.title("📊 Data Portal Viewer")

# -------------------------
# helper
# -------------------------
def clear_fetched_data():
    """Clear stored dataset when user changes selection."""
    for key in ("df", "col_suggestions", "filtered_df"):
        if key in st.session_state:
            del st.session_state[key]

# -------------------------
# dataset selector
# -------------------------
selected_dataset = st.selectbox(
    "Choose a dataset:",
    list(DATASETS.keys()),
    key="dataset_select"
)

# clear previous data when dataset changes
if st.session_state.get("last_dataset") != selected_dataset:
    clear_fetched_data()
    st.session_state["last_dataset"] = selected_dataset

# -------------------------
# fetch button
# -------------------------
if st.button("Fetch Data", key="fetch_data_btn"):
    resource_id = DATASETS[selected_dataset]
    with st.spinner(f"Fetching data for **{selected_dataset}**..."):
        df, col_suggestions = fetch_from_api(resource_id)
    st.session_state["df"] = df
    st.session_state["col_suggestions"] = col_suggestions

# -------------------------
# show fetched dataset
# -------------------------
if "df" in st.session_state and st.session_state["df"] is not None and not st.session_state["df"].empty:
    df = st.session_state["df"]
    col_suggestions = st.session_state.get("col_suggestions", {})

    st.success(f"✅ Successfully fetched {len(df)} records for **{selected_dataset}**")

    # Column Suggestions
    # === COLUMN SUGGESTIONS (Compact Version) ===
    with st.expander("💡 Column Overview (click to expand/minimize)", expanded=False):
        if isinstance(col_suggestions, dict) and col_suggestions:
            cols_md = []
            for col, info in col_suggestions.items():
                cols_md.append(
                    f"- **{col}** — {info['dtype']}, unique={info['num_unique']}, missing={info['num_missing']}"
                )
            st.markdown("\n".join(cols_md))
        else:
            st.info("⚠️ Column suggestions are not available for this dataset.")

    # --- FILTER SECTION ---
st.markdown("### 🎛️ Filters")

filtered_df = None  # ✅ Always define it first to avoid NameError

if df is not None and not df.empty:
    # Identify suitable columns
    categorical_cols = [c for c in df.columns if df[c].dtype == "object" or df[c].nunique() <= 20]
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    if not categorical_cols and not numeric_cols:
        st.info("No suitable filters found for this dataset.")
        filtered_df = df.copy()
    else:
        filtered_df = df.copy()

        # --- Categorical Filters ---
        if categorical_cols:
            with st.expander("🔹 Categorical Filters", expanded=False):
                for col in categorical_cols:
                    unique_vals = df[col].dropna().unique().tolist()
                    if len(unique_vals) > 1:
                        selected_vals = st.multiselect(f"Filter **{col}**:", unique_vals, default=unique_vals)
                        filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]
        else:
            st.info("No suitable categorical filters found for this dataset.")

        # --- Numeric Filters ---
        if numeric_cols:
            with st.expander("🔹 Numeric Filters", expanded=False):
                for col in numeric_cols:
                    min_val, max_val = float(df[col].min()), float(df[col].max())
                    selected_range = st.slider(f"Filter **{col}** range:", min_val, max_val, (min_val, max_val))
                    filtered_df = filtered_df[(filtered_df[col] >= selected_range[0]) & (filtered_df[col] <= selected_range[1])]
        else:
            st.info("No suitable numeric filters found for this dataset.")





    # Results
    st.markdown("### 🔹 Filtered Results")
    if filtered_df.empty:
        st.warning("No records match the selected filters.")
    else:
        st.dataframe(filtered_df)

    # Download button
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Filtered Data as CSV",
        data=csv,
        file_name=f"{selected_dataset.replace(' ', '_')}_filtered.csv",
        mime="text/csv"
    )

        # Comparison
    st.markdown("### 🔍 Compare with Another Dataset (Optional)")
    compare_choice = st.selectbox("Compare with:", ["None"] + list(DATASETS.keys()), key="compare_select")

    if compare_choice != "None":
        compare_id = DATASETS[compare_choice]
        with st.spinner(f"Fetching comparison dataset: {compare_choice} ..."):
            df2, _ = fetch_from_api(compare_id)

        if df2 is not None and not df2.empty:
            # Normalize column names (case-insensitive matching)
            df.columns = [c.strip().lower() for c in df.columns]
            df2.columns = [c.strip().lower() for c in df2.columns]

            common_cols = list(set(df.columns).intersection(set(df2.columns)))

            if not common_cols:
                st.error("❌ No common columns found between the two datasets. Unable to compare.")
            else:
                st.info(f"Common columns detected: {', '.join(common_cols)}")

                # Try comparing on 'year' or similar column if available
                preferred_keys = ["year", "yr", "years"]
                key_col = next((c for c in preferred_keys if c in common_cols), None)

                try:
                    if key_col:
                        merged = pd.merge(df, df2, on=key_col, how="inner", suffixes=("_ds1", "_ds2"))
                        st.success(f"✅ Compared on '{key_col}' column. Showing first 100 rows:")
                        st.dataframe(merged.head(100))
                    else:
                        # fallback — show side-by-side preview
                        st.warning("⚠️ No 'year'-like column found. Showing side-by-side preview of both datasets.")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**{selected_dataset}** sample:")
                            st.dataframe(df.head(50))
                        with c2:
                            st.write(f"**{compare_choice}** sample:")
                            st.dataframe(df2.head(50))
                except Exception as e:
                    st.error(f"Error while comparing: {e}")
        else:
            st.error("Could not fetch the comparison dataset.")


# Footer
st.markdown("---")
st.caption("Powered by data.gov.in | Built with ❤️ using Streamlit")
