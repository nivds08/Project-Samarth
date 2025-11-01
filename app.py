# app.py
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
st.title("📊 Data Portal Viewer")

# -------------------------
# helper utilities
# -------------------------
def clear_fetched_data():
    """Clear stored dataset when user changes selection."""
    for key in ("df", "col_suggestions", "filtered_df", "user_query"):
        if key in st.session_state:
            del st.session_state[key]

def extract_filters_from_query(query: str, df: pd.DataFrame):
    """
    Very simple keyword matching:
    find column values that appear in query string (case-insensitive).
    Returns dict {col: matched_value}.
    """
    query = str(query).lower()
    filters = {}
    # check columns with reasonable unique counts first (avoid huge loops)
    for col in df.columns:
        # sample unique values to check (if huge, check top frequent values)
        try:
            uniques = df[col].dropna().astype(str).unique()
        except Exception:
            continue
        # small optimization: only check values longer than 2 chars
        for val in uniques:
            vs = str(val).lower()
            if len(vs) > 2 and vs in query:
                filters[col] = val
                break
    return filters

# -------------------------
# dataset selector
# -------------------------
selected_dataset = st.selectbox(
    "Choose a dataset:",
    list(DATASETS.keys()),
    key="dataset_select"
)

# if user changed dataset since last run, clear previous fetch
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
    # store into session_state so it persists across reruns
    st.session_state["df"] = df
    st.session_state["col_suggestions"] = col_suggestions
    # also clear any previous filtered_df/user query
    st.session_state.pop("filtered_df", None)
    st.session_state.pop("user_query", None)

# -------------------------
# If dataset is already fetched (in session), show UI and allow query/filter
# -------------------------
if "df" in st.session_state and st.session_state["df"] is not None and not st.session_state["df"].empty:
    df = st.session_state["df"]
    col_suggestions = st.session_state.get("col_suggestions", {})

    st.success(f"✅ Successfully fetched {len(df)} records for **{selected_dataset}**")

    # show column suggestions (if available)
    st.markdown("### 🔹 Column Suggestions")
    if isinstance(col_suggestions, dict) and col_suggestions:
        # show compact summary
        cols_md = []
        for col, info in col_suggestions.items():
            cols_md.append(f"- **{col}** — {info['dtype']}, unique={info['num_unique']}, missing={info['num_missing']}")
        st.write("\n".join(cols_md))
    else:
        st.warning("⚠️ Column suggestions are not available for this dataset.")

    # Query input (stored in session so it survives Enter/rerun)
    st.markdown("### 🧠 Ask a question (natural language)")
    if "user_query" not in st.session_state:
        st.session_state["user_query"] = ""
    user_query = st.text_input(
        "Type something like: 'rainfall in Kerala 2010' or 'paddy production Punjab 2019'",
        value=st.session_state.get("user_query", ""),
        key="user_query_input"
    )
    # save to session explicitly so Enter doesn't drop it
    st.session_state["user_query"] = user_query

    # apply query-based filtering (if query present)
    filtered_df = df.copy()
    if user_query and user_query.strip():
        filters = extract_filters_from_query(user_query, df)
        if filters:
            st.info(f"Detected filters from query: {filters}")
            for col, val in filters.items():
                # filter robustly (string compare)
                filtered_df = filtered_df[filtered_df[col].astype(str).str.lower() == str(val).lower()]
        else:
            st.warning("Could not detect exact matches for your query — try different wording or use manual filters below.")

    # Manual filters (fallback)
    st.markdown("### ⚙️ Manual Filters (optional)")
    # Put manual filters in an expander so UI isn't overwhelming
    with st.expander("Show manual filters"):
        # iterate columns and create widgets with unique keys
        for col in df.columns:
            safe_key = f"filter__{col}"
            # categorical-ish handling
            try:
                if df[col].dtype == "object" or df[col].nunique() <= 30:
                    unique_vals = df[col].dropna().astype(str).unique().tolist()
                    # default empty (so user has to pick) — prevents showing all by default
                    sel = st.multiselect(f"{col}", unique_vals, default=[], key=safe_key)
                    if sel:
                        filtered_df = filtered_df[filtered_df[col].astype(str).isin(sel)]
                elif pd.api.types.is_numeric_dtype(df[col]):
                    min_val = float(df[col].min())
                    max_val = float(df[col].max())
                    key_slider = f"slider__{col}"
                    sel_range = st.slider(f"{col}", min_val, max_val, (min_val, max_val), key=key_slider)
                    # apply slider only if user changed it away from full range
                    if sel_range != (min_val, max_val):
                        filtered_df = filtered_df[(filtered_df[col] >= sel_range[0]) & (filtered_df[col] <= sel_range[1])]
                else:
                    # for everything else, skip automatic filtering widget
                    pass
            except Exception:
                # protect against weird column types
                continue

    # display filtered data
    st.markdown("### 🔹 Results")
    if filtered_df.empty:
        st.warning("No records match the current query/filters.")
    else:
        st.dataframe(filtered_df)

    # allow download of the filtered dataframe
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download results as CSV", data=csv,
                       file_name=f"{selected_dataset.replace(' ', '_')}_results.csv",
                       mime="text/csv", key="download_btn")

    # optional comparison (use filtered_df for comparing)
    st.markdown("### 🔍 Compare with another dataset")
    compare_choice = st.selectbox("Compare with:", ["None"] + list(DATASETS.keys()), key="compare_select")
    if compare_choice != "None":
        compare_id = DATASETS[compare_choice]
        with st.spinner(f"Fetching comparison dataset: {compare_choice} ..."):
            df2, _ = fetch_from_api(compare_id)
        if df2 is not None and not df2.empty:
            try:
                comparison_result = compare_states(filtered_df, df2)
                st.dataframe(comparison_result)
            except Exception as e:
                st.error(f"Error while comparing: {e}")
        else:
            st.error("Could not fetch the comparison dataset.")

# footer
st.markdown("---")
st.caption("Powered by data.gov.in | Built with ❤️ using Streamlit")
