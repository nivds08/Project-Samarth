# app.py
import sys
import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# make src importable
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.data_handler.fetch_manager import fetch_from_api
from src.query_engine.executor import compare_states  # keep using it if present

load_dotenv()

# -------------------------
# Dataset mapping (resource IDs)
# -------------------------
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

# -------------------------
# Page config & small CSS
# -------------------------
st.set_page_config(page_title="Project-Samarth", layout="wide")
st.markdown(
    """
    <style>
    /* pointer on selectboxes */
    div[data-baseweb="select"] > div { cursor: pointer !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🚀 Project Samarth")
st.markdown("_An intelligent data exploration platform powered by open government datasets._")

# -------------------------
# Helpers
# -------------------------
def clear_fetched_data():
    for k in ("df", "col_suggestions", "filtered_df"):
        st.session_state.pop(k, None)

def is_month_col_name(col_name: str) -> bool:
    c = col_name.lower()
    months = ("jan","feb","mar","apr","may","jun","jul","aug","sep","sept","oct","nov","dec",
              "january","february","march","april","may","june","july","august","september","october","november","december")
    return any(m in c for m in months)

def looks_like_value_column(series: pd.Series) -> bool:
    # True when the column is numeric OR has many unique numeric-like values
    if pd.api.types.is_numeric_dtype(series):
        return True
    try:
        unique = series.dropna().astype(str).unique()
        # if most unique values are numeric-like and there are many, consider value column
        if len(unique) > 50 and sum(1 for v in unique if v.replace('.', '', 1).isdigit()) / len(unique) > 0.6:
            return True
    except Exception:
        pass
    return False

# -------------------------
# Dataset selection
# -------------------------
selected_dataset = st.selectbox("Choose a dataset:", list(DATASETS.keys()), key="dataset_select")

# clear stored data when dataset changes
if st.session_state.get("last_dataset") != selected_dataset:
    clear_fetched_data()
    st.session_state["last_dataset"] = selected_dataset

# -------------------------
# Fetch data button
# -------------------------
if st.button("Fetch Data", key="fetch_data_btn"):
    resource_id = DATASETS[selected_dataset]
    with st.spinner(f"Fetching data for **{selected_dataset}**..."):
        df, col_suggestions = fetch_from_api(resource_id)
    st.session_state["df"] = df
    st.session_state["col_suggestions"] = col_suggestions
    st.session_state.pop("filtered_df", None)

# -------------------------
# Show UI only when df exists
# -------------------------
if "df" in st.session_state and st.session_state["df"] is not None and not st.session_state["df"].empty:
    df = st.session_state["df"].copy()
    col_suggestions = st.session_state.get("col_suggestions", {})

    st.success(f"✅ Successfully fetched {len(df)} records for **{selected_dataset}**")

    # Compact column suggestions in an expander
    with st.expander("📋 Column Overview", expanded=False):
        if isinstance(col_suggestions, dict) and col_suggestions:
            for col, info in col_suggestions.items():
                st.markdown(f"**{col}** — {info['dtype']}, unique={info['num_unique']}, missing={info['num_missing']}")
        else:
            st.info("Column suggestions not available for this dataset.")

    # -------------------------
    # Smart filters
    # -------------------------
    st.markdown("### 🎛️ Filters")
    # initialize filtered_df so it's always defined
    filtered_df = df.copy()

    # Determine candidate categorical and numeric columns
    # Exclude obvious month/value columns from categorical candidates
    categorical_candidates = []
    numeric_candidates = []
    for col in df.columns:
        try:
            if is_month_col_name(col) or looks_like_value_column(df[col]):
                # don't present these as categorical filters
                if pd.api.types.is_numeric_dtype(df[col]):
                    numeric_candidates.append(col)
                else:
                    # treat as numeric-like (skip categorical)
                    numeric_candidates.append(col)
            else:
                # candidate for categorical filter if not too many uniques
                n_unique = df[col].nunique(dropna=True)
                if n_unique <= 200 and (df[col].dtype == "object" or n_unique <= 50):
                    categorical_candidates.append(col)
                elif pd.api.types.is_numeric_dtype(df[col]):
                    numeric_candidates.append(col)
        except Exception:
            continue

    if not categorical_candidates and not numeric_candidates:
        st.info("No suitable filters found for this dataset.")
    else:
        with st.expander("Show filter options", expanded=False):
            # Categorical filters (multiselect) — defaults to empty so not preselecting everything
            for col in categorical_candidates:
                try:
                    options = df[col].dropna().astype(str).unique().tolist()
                    options = sorted(options, key=lambda x: (str(x).lower()))
                    if len(options) <= 500:  # safety guard
                        sel = st.multiselect(f"{col}", options, default=[], key=f"filter_{col}")
                        if sel:
                            filtered_df = filtered_df[filtered_df[col].astype(str).isin(sel)]
                except Exception:
                    continue

            # Numeric filters (sliders)
            for col in numeric_candidates:
                try:
                    # numeric columns may be floats/ints stored as strings — try to coerce where possible
                    ser = pd.to_numeric(df[col], errors="coerce") if not pd.api.types.is_numeric_dtype(df[col]) else df[col]
                    if ser.dropna().empty:
                        continue
                    min_val = float(ser.min())
                    max_val = float(ser.max())
                    if min_val == max_val:
                        continue
                    sel_range = st.slider(f"{col} range", min_val, max_val, (min_val, max_val), key=f"slider_{col}")
                    # apply only if slider moved
                    if sel_range != (min_val, max_val):
                        filtered_df = filtered_df[(pd.to_numeric(filtered_df[col], errors="coerce") >= sel_range[0]) &
                                                  (pd.to_numeric(filtered_df[col], errors="coerce") <= sel_range[1])]
                except Exception:
                    continue

    # store filtered_df into session (optional)
    st.session_state["filtered_df"] = filtered_df

    # -------------------------
    # Results & download
    # -------------------------
    st.markdown("### 🔹 Filtered Results")
    if filtered_df.empty:
        st.warning("No records match the selected filters.")
    else:
        st.dataframe(filtered_df)

    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download results as CSV",
                       data=csv,
                       file_name=f"{selected_dataset.replace(' ', '_')}_results.csv",
                       mime="text/csv",
                       key="download_btn")

    # -------------------------
    # Robust comparison
    # -------------------------
    st.markdown("### 🔍 Compare with another dataset (Optional)")
    compare_choice = st.selectbox("Compare with:", ["None"] + list(DATASETS.keys()), key="compare_select")
    if compare_choice != "None":
        compare_id = DATASETS[compare_choice]
        with st.spinner(f"Fetching comparison dataset: {compare_choice} ..."):
            df2, _ = fetch_from_api(compare_id)

        if df2 is not None and not df2.empty:
            try:
                # do not mutate original df names: create normalized copies for matching
                df_norm = df.copy()
                df2_norm = df2.copy()
                df_norm.columns = [c.strip().lower() for c in df_norm.columns]
                df2_norm.columns = [c.strip().lower() for c in df2_norm.columns]

                common_cols = list(set(df_norm.columns).intersection(set(df2_norm.columns)))
                if not common_cols:
                    st.error("❌ No common columns found between the two datasets. Showing side-by-side preview instead.")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**{selected_dataset}** preview")
                        st.dataframe(df.head(50))
                    with c2:
                        st.write(f"**{compare_choice}** preview")
                        st.dataframe(df2.head(50))
                else:
                    st.info(f"Common columns: {', '.join(common_cols[:10])}")
                    # prefer year-like columns for merge
                    pref = next((c for c in ["year", "yr"] if c in common_cols), None)
                    key_col = pref if pref else common_cols[0]
                    # merge using normalized column name, but show readable results
                    merged = pd.merge(df_norm, df2_norm, on=key_col, how="inner", suffixes=("_left", "_right"))
                    if merged.empty:
                        st.warning("Merge resulted in no rows. Showing side-by-side preview.")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.dataframe(df.head(50))
                        with c2:
                            st.dataframe(df2.head(50))
                    else:
                        st.success(f"✅ Merged on `{key_col}` — showing first 100 rows")
                        st.dataframe(merged.head(100))
            except Exception as e:
                st.error(f"Error while comparing: {e}")
        else:
            st.error("Could not fetch the comparison dataset.")

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.caption("Powered by data.gov.in | Built with ❤️ using Streamlit")
