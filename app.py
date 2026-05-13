# app.py
import sys
import os
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")  # headless servers (Railway/Docker) — must be before pyplot
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from pandas.api.types import is_numeric_dtype
from sklearn.linear_model import LinearRegression
from scipy.stats import linregress
import time

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
    /* Brighter, cleaner app shell */
    .stApp {
        background: linear-gradient(180deg, #f7faff 0%, #eef6ff 100%);
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        color: #0f2a56;
    }
    /* pointer on selectboxes */
    div[data-baseweb="select"] > div {
        cursor: pointer !important;
        border-radius: 10px;
        border-color: #9dc4ff !important;
    }
    /* Section cards */
    .samarth-card {
        background: #ffffff;
        border: 1px solid #dbe9ff;
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 6px 18px rgba(64, 124, 214, 0.08);
    }
    /* Buttons */
    .stButton > button, .stDownloadButton > button {
        background: linear-gradient(90deg, #1f77ff 0%, #3d8bff 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        filter: brightness(1.08);
        transform: translateY(-1px);
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🚀 Project Samarth")
st.markdown("_An intelligent data exploration platform powered by open government datasets._")
st.markdown('<div class="samarth-card">Use smart filters to narrow results quickly and export only what matters.</div>', unsafe_allow_html=True)

# -------------------------
# Helpers
# -------------------------
def clear_fetched_data():
    for k in ("df", "col_suggestions", "filtered_df", "last_fetch_error"):
        st.session_state.pop(k, None)

def render_fetch_error(error: dict | None, *, context: str):
    if not error:
        st.error(f"❌ {context} failed, but no error details were provided.")
        return
    kind = error.get("kind", "unknown_error")
    message = error.get("message", "Unknown error")
    status = error.get("status_code")
    url = error.get("url")
    attempt = error.get("attempt")
    max_retries = error.get("max_retries")
    timeout_s = error.get("timeout_s")

    headline = f"❌ {context} failed: {kind}"
    st.error(headline)
    st.write(message)
    with st.expander("View technical details", expanded=False):
        if status is not None:
            st.write(f"HTTP status: {status}")
        if url:
            st.write(f"URL: `{url}`")
        if attempt is not None and max_retries is not None:
            st.write(f"Attempt: {attempt} / {max_retries}")
        if timeout_s is not None:
            st.write(f"Timeout (seconds): {timeout_s}")
        preview = error.get("response_preview")
        if preview:
            st.code(preview)
        keys = error.get("top_level_keys")
        if keys:
            st.write(f"Top-level JSON keys: {keys}")

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

def normalize_text(value):
    """Normalize values for resilient, case-insensitive categorical matching."""
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text.casefold() if text else None

def build_filter_candidates(df: pd.DataFrame):
    categorical_candidates = []
    numeric_candidates = []
    skipped_columns = []

    for col in df.columns:
        try:
            series = df[col]
            n_unique = series.nunique(dropna=True)
            if n_unique == 0:
                skipped_columns.append((col, "all values missing"))
                continue

            if is_month_col_name(col) or looks_like_value_column(series):
                numeric_candidates.append(col)
                continue

            if n_unique <= 200 and (series.dtype == "object" or n_unique <= 50):
                categorical_candidates.append(col)
            elif is_numeric_dtype(series):
                numeric_candidates.append(col)
            else:
                skipped_columns.append((col, f"high cardinality ({n_unique} unique)"))
        except Exception as err:
            skipped_columns.append((col, f"analysis error: {err}"))

    return categorical_candidates, numeric_candidates, skipped_columns

def apply_categorical_filter(dataframe: pd.DataFrame, column: str, selected_values):
    if not selected_values:
        return dataframe, None

    try:
        normalized_selected = {normalize_text(v) for v in selected_values if normalize_text(v) is not None}
        if not normalized_selected:
            return dataframe, f"Skipped `{column}` because no valid filter values were selected."

        normalized_column = dataframe[column].map(normalize_text)
        mask = normalized_column.isin(normalized_selected)
        return dataframe[mask], None
    except KeyError:
        return dataframe, f"Skipped `{column}` because the column is missing after previous filter operations."
    except Exception as err:
        return dataframe, f"Could not apply categorical filter on `{column}`: {err}"

def apply_numeric_filter(dataframe: pd.DataFrame, column: str, selected_range):
    try:
        numeric_series = pd.to_numeric(dataframe[column], errors="coerce")
        if numeric_series.dropna().empty:
            return dataframe, f"Skipped numeric filter for `{column}` because values are not numeric."

        low, high = selected_range
        if low > high:
            return dataframe, f"Skipped `{column}` due to invalid range ({low} > {high})."

        mask = numeric_series.between(low, high, inclusive="both")
        return dataframe[mask], None
    except KeyError:
        return dataframe, f"Skipped `{column}` because the column is missing after previous filter operations."
    except Exception as err:
        return dataframe, f"Could not apply numeric filter on `{column}`: {err}"

def find_column_by_keywords(df: pd.DataFrame, keywords, prefer_numeric=False):
    matches = []
    for col in df.columns:
        col_norm = str(col).strip().lower()
        if any(k in col_norm for k in keywords):
            matches.append(col)
    if not matches:
        return None
    if prefer_numeric:
        numeric_matches = [c for c in matches if is_numeric_dtype(df[c])]
        if numeric_matches:
            return numeric_matches[0]
    return matches[0]

def _numeric_candidate_columns(df: pd.DataFrame):
    candidates = []
    for c in df.columns:
        try:
            ser = pd.to_numeric(df[c], errors="coerce") if not is_numeric_dtype(df[c]) else df[c]
            non_null = int(ser.notna().sum())
            if non_null == 0:
                continue
            candidates.append((c, non_null))
        except Exception:
            continue
    # Most-filled numeric-like columns first
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in candidates]

def _best_numeric_fallback(df: pd.DataFrame, *, exclude_cols: set[str]):
    for c in _numeric_candidate_columns(df):
        if c not in exclude_cols:
            return c
    return None

def prepare_rainfall_columns(df: pd.DataFrame):
    year_col = find_column_by_keywords(df, ["year", "yr"])
    rainfall_col = find_column_by_keywords(df, ["rain", "rainfall", "precip"], prefer_numeric=True)
    region_col = (
        find_column_by_keywords(df, ["district", "dist"]) or
        find_column_by_keywords(df, ["state", "st_name", "state_name"]) or
        find_column_by_keywords(df, ["subdivision", "sub_division", "sub-division"])
    )
    # Fallback: some rainfall datasets store totals under generic names (e.g., "annual", "total")
    if rainfall_col is None:
        rainfall_col = find_column_by_keywords(df, ["annual", "total", "sum", "value"], prefer_numeric=True)
    # Final fallback: pick the best-filled numeric column excluding obvious ids
    if rainfall_col is None:
        exclude = {c for c in [year_col, region_col] if c}
        rainfall_col = _best_numeric_fallback(df, exclude_cols=exclude)
    return year_col, rainfall_col, region_col

def prepare_crop_columns(df: pd.DataFrame):
    year_col = find_column_by_keywords(df, ["year", "yr"])
    crop_col = find_column_by_keywords(df, ["crop", "commodity", "item"])
    yield_col = find_column_by_keywords(df, ["yield"], prefer_numeric=True)
    if yield_col is None:
        yield_col = find_column_by_keywords(df, ["production", "prod"], prefer_numeric=True)
    if yield_col is None:
        yield_col = find_column_by_keywords(df, ["output", "quantity", "qty", "value", "area"], prefer_numeric=True)
    if yield_col is None:
        exclude = {c for c in [year_col, crop_col] if c}
        yield_col = _best_numeric_fallback(df, exclude_cols=exclude)
    region_col = (
        find_column_by_keywords(df, ["district", "dist"]) or
        find_column_by_keywords(df, ["state", "st_name", "state_name"])
    )
    return year_col, crop_col, yield_col, region_col

@st.cache_data(show_spinner=False)
def get_analysis_dataset(resource_id: str):
    fetched_df, _, fetch_error = fetch_from_api(resource_id)
    return fetched_df, fetch_error

def correlation_interpretation(score: float) -> str:
    if score > 0.7:
        return "Strong positive correlation"
    if 0.4 <= score <= 0.7:
        return "Moderate positive correlation"
    return "Weak or no significant correlation"

def render_mapping_debug(title: str, mapping: dict):
    st.markdown(f"**{title}**")
    debug_df = pd.DataFrame(
        [{"Field": k, "Detected Column": (v if v else "Not detected")} for k, v in mapping.items()]
    )
    st.dataframe(debug_df, use_container_width=True, hide_index=True)

def missing_fields_message(field_map: dict) -> str:
    missing = [name for name, value in field_map.items() if not value]
    if not missing:
        return ""
    return ", ".join(missing)

def fetch_dataset_with_feedback(resource_id: str, dataset_name: str):
    with st.spinner(f"Loading `{dataset_name}` for analysis..."):
        fetched, err = get_analysis_dataset(resource_id)
    if fetched is None or fetched.empty:
        render_fetch_error(err, context=f"Loading `{dataset_name}`")
        return None
    return fetched

# -------------------------
# Dataset selection
# -------------------------
selected_dataset = st.selectbox("Choose a dataset:", list(DATASETS.keys()), key="dataset_select")

# clear stored data when dataset changes
if st.session_state.get("last_dataset") != selected_dataset:
    clear_fetched_data()
    st.session_state["last_dataset"] = selected_dataset

# Quick connectivity test (limit=1) to differentiate code bugs vs network blocks
with st.expander("🔌 API connectivity test", expanded=False):
    st.caption("Runs a tiny request (limit=1) to check whether data.gov.in is reachable from this machine/network.")
    if st.button("Test data.gov.in API", key="test_api_btn"):
        test_id = DATASETS[selected_dataset]
        start = time.time()
        with st.spinner("Testing API connectivity..."):
            test_df, _, test_err = fetch_from_api(test_id, limit=1, timeout_s=20, max_retries=1)
        elapsed_ms = int((time.time() - start) * 1000)
        if test_err is None and test_df is not None and not test_df.empty:
            st.success(f"✅ API reachable. Received {len(test_df)} row(s) in {elapsed_ms} ms.")
        else:
            st.warning(f"⚠️ API test did not return records (took {elapsed_ms} ms).")
            if test_err is None:
                render_fetch_error(
                    {
                        "kind": "no_records",
                        "message": "The API request succeeded but returned 0 records for this dataset.",
                    },
                    context="API connectivity test",
                )
            else:
                render_fetch_error(test_err, context="API connectivity test")

# -------------------------
# Fetch data button
# -------------------------
if st.button("Fetch Data", key="fetch_data_btn"):
    resource_id = DATASETS[selected_dataset]
    with st.spinner(f"Fetching data for **{selected_dataset}**..."):
        df, col_suggestions, fetch_error = fetch_from_api(resource_id)
    if fetch_error is None and (df is None or df.empty):
        fetch_error = {
            "kind": "no_records",
            "message": "The API request succeeded but returned 0 records for this dataset (try another dataset or increase limit).",
        }
    st.session_state["df"] = df
    st.session_state["col_suggestions"] = col_suggestions
    st.session_state["last_fetch_error"] = fetch_error
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
    categorical_candidates, numeric_candidates, skipped_columns = build_filter_candidates(df)
    filter_errors = []

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
                            filtered_df, err = apply_categorical_filter(filtered_df, col, sel)
                            if err:
                                filter_errors.append(err)
                    else:
                        filter_errors.append(
                            f"Skipped `{col}` because it has too many options ({len(options)} unique values)."
                        )
                except Exception as err:
                    filter_errors.append(f"Could not render categorical filter `{col}`: {err}")

            # Numeric filters (sliders)
            for col in numeric_candidates:
                try:
                    # numeric columns may be floats/ints stored as strings — try to coerce where possible
                    ser = pd.to_numeric(df[col], errors="coerce") if not is_numeric_dtype(df[col]) else df[col]
                    if ser.dropna().empty:
                        continue
                    min_val = float(ser.min())
                    max_val = float(ser.max())
                    if min_val == max_val:
                        continue
                    sel_range = st.slider(f"{col} range", min_val, max_val, (min_val, max_val), key=f"slider_{col}")
                    # apply only if slider moved
                    if sel_range != (min_val, max_val):
                        filtered_df, err = apply_numeric_filter(filtered_df, col, sel_range)
                        if err:
                            filter_errors.append(err)
                except Exception as err:
                    filter_errors.append(f"Could not render numeric filter `{col}`: {err}")

    if skipped_columns:
        with st.expander("ℹ️ Filter diagnostics", expanded=False):
            for col_name, reason in skipped_columns:
                st.caption(f"Skipped `{col_name}`: {reason}")
    if filter_errors:
        st.warning("Some filters were skipped due to edge cases.")
        with st.expander("View filter warnings", expanded=False):
            for message in filter_errors:
                st.write(f"- {message}")

    # store filtered_df into session (optional)
    st.session_state["filtered_df"] = filtered_df

    # -------------------------
    # Column mapping debug
    # -------------------------
    current_rain_year, current_rainfall, current_rain_region = prepare_rainfall_columns(filtered_df)
    current_crop_year, current_crop_name, current_crop_yield, current_crop_region = prepare_crop_columns(filtered_df)
    with st.expander("🧭 Column Mapping Debug", expanded=False):
        st.caption("Shows auto-detected columns used by charts, correlation, and prediction features.")

        render_mapping_debug(
            "Current Filtered Dataset",
            {
                "Rainfall Year": current_rain_year,
                "Rainfall Value": current_rainfall,
                "Rainfall Region": current_rain_region,
                "Crop Year": current_crop_year,
                "Crop Name": current_crop_name,
                "Crop Yield/Production": current_crop_yield,
                "Crop Region": current_crop_region,
            },
        )

        if st.button("Load Correlation Source Mappings", key="load_corr_mapping_debug_btn"):
            try:
                debug_rain_df = fetch_dataset_with_feedback(
                    DATASETS["District-rainfall"], "District-rainfall"
                )
                debug_crop_df = fetch_dataset_with_feedback(
                    DATASETS["District Crop Production (1997)"], "District Crop Production (1997)"
                )

                if debug_rain_df is not None:
                    debug_rain_year, debug_rainfall, debug_rain_region = prepare_rainfall_columns(debug_rain_df)
                    render_mapping_debug(
                        "Correlation Source: District-rainfall",
                        {
                            "Rainfall Year": debug_rain_year,
                            "Rainfall Value": debug_rainfall,
                            "Region (District/State)": debug_rain_region,
                        },
                    )

                if debug_crop_df is not None:
                    debug_crop_year, debug_crop_name, debug_crop_yield, debug_crop_region = prepare_crop_columns(debug_crop_df)
                    render_mapping_debug(
                        "Correlation Source: District Crop Production (1997)",
                        {
                            "Crop Year": debug_crop_year,
                            "Crop Name": debug_crop_name,
                            "Crop Yield/Production": debug_crop_yield,
                            "Region (District/State)": debug_crop_region,
                        },
                    )
            except Exception as debug_err:
                st.warning(f"Mapping debug for correlation sources is unavailable: {debug_err}")
        else:
            st.info("Click `Load Correlation Source Mappings` only when needed. This avoids extra API calls.")

    # -------------------------
    # Results, visualizations, analysis
    # -------------------------
    st.markdown("### 🔹 Filtered Results")
    table_tab, chart_tab = st.tabs(["Table View", "Chart View"])

    with table_tab:
        if filtered_df.empty:
            st.warning("No records match the selected filters.")
        else:
            st.caption(f"Showing {len(filtered_df)} of {len(df)} rows after filtering.")
            st.dataframe(filtered_df)

    with chart_tab:
        if filtered_df.empty:
            st.warning("No records available to visualize. Adjust filters and try again.")
        else:
            with st.expander("📈 Visualizations", expanded=False):
                rain_year_col, rain_value_col, _ = prepare_rainfall_columns(filtered_df)
                crop_year_col, crop_name_col, crop_yield_col, _ = prepare_crop_columns(filtered_df)

                if rain_year_col and rain_value_col:
                    rain_plot_df = filtered_df[[rain_year_col, rain_value_col]].copy()
                    rain_plot_df[rain_year_col] = pd.to_numeric(rain_plot_df[rain_year_col], errors="coerce")
                    rain_plot_df[rain_value_col] = pd.to_numeric(rain_plot_df[rain_value_col], errors="coerce")
                    rain_plot_df = rain_plot_df.dropna().sort_values(rain_year_col)
                    if not rain_plot_df.empty:
                        rain_trend = rain_plot_df.groupby(rain_year_col, as_index=False)[rain_value_col].mean()
                        fig, ax = plt.subplots(figsize=(10, 4))
                        ax.plot(rain_trend[rain_year_col], rain_trend[rain_value_col], marker="o", label="Rainfall trend")
                        ax.set_title("Rainfall Trend Over Years")
                        ax.set_xlabel("Year")
                        ax.set_ylabel("Rainfall")
                        ax.legend()
                        ax.grid(alpha=0.3)
                        st.pyplot(fig)
                    else:
                        st.warning("Rainfall trend chart needs valid numeric year and rainfall values.")
                else:
                    missing_msg = missing_fields_message(
                        {"Rainfall Year": rain_year_col, "Rainfall Value": rain_value_col}
                    )
                    st.error(
                        f"Rainfall trend chart unavailable. Missing required mapping(s): {missing_msg}. "
                        "Check `Column Mapping Debug`."
                    )
                    st.info("Tip: choose the correct columns manually below.")
                    manual_year_opts = []
                    for c in filtered_df.columns:
                        c_norm = str(c).strip().lower()
                        if "year" in c_norm or c_norm in {"yr", "year"}:
                            manual_year_opts.append(c)
                    manual_year_opts += _numeric_candidate_columns(filtered_df)
                    manual_year_opts = list(dict.fromkeys(manual_year_opts))

                    manual_val_opts = _numeric_candidate_columns(filtered_df)
                    manual_val_opts = list(dict.fromkeys(manual_val_opts))

                    c1, c2 = st.columns(2)
                    with c1:
                        picked_year = st.selectbox(
                            "Rainfall chart: pick year column",
                            options=manual_year_opts,
                            index=0 if manual_year_opts else None,
                            key="manual_rain_year_col",
                        )
                    with c2:
                        picked_val = st.selectbox(
                            "Rainfall chart: pick value column",
                            options=manual_val_opts,
                            index=0 if manual_val_opts else None,
                            key="manual_rain_value_col",
                        )
                    if picked_year and picked_val:
                        try:
                            rain_plot_df = filtered_df[[picked_year, picked_val]].copy()
                            rain_plot_df[picked_year] = pd.to_numeric(rain_plot_df[picked_year], errors="coerce")
                            rain_plot_df[picked_val] = pd.to_numeric(rain_plot_df[picked_val], errors="coerce")
                            rain_plot_df = rain_plot_df.dropna().sort_values(picked_year)
                            if not rain_plot_df.empty:
                                rain_trend = rain_plot_df.groupby(picked_year, as_index=False)[picked_val].mean()
                                fig, ax = plt.subplots(figsize=(10, 4))
                                ax.plot(rain_trend[picked_year], rain_trend[picked_val], marker="o", label="Rainfall trend")
                                ax.set_title("Rainfall Trend Over Years (manual mapping)")
                                ax.set_xlabel(str(picked_year))
                                ax.set_ylabel(str(picked_val))
                                ax.legend()
                                ax.grid(alpha=0.3)
                                st.pyplot(fig)
                        except Exception as e:
                            st.warning(f"Could not render manual rainfall trend chart: {e}")

                if crop_name_col and crop_yield_col:
                    crop_plot_df = filtered_df[[crop_name_col, crop_yield_col]].copy()
                    crop_plot_df[crop_yield_col] = pd.to_numeric(crop_plot_df[crop_yield_col], errors="coerce")
                    crop_plot_df = crop_plot_df.dropna()
                    if not crop_plot_df.empty:
                        crop_compare = (
                            crop_plot_df.groupby(crop_name_col, as_index=False)[crop_yield_col]
                            .mean()
                            .sort_values(crop_yield_col, ascending=False)
                            .head(15)
                        )
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.bar(crop_compare[crop_name_col].astype(str), crop_compare[crop_yield_col], label="Average yield")
                        ax.set_title("Crop Yield Comparison Across Crops")
                        ax.set_xlabel("Crop")
                        ax.set_ylabel("Yield")
                        ax.legend()
                        ax.tick_params(axis="x", rotation=45)
                        ax.grid(axis="y", alpha=0.3)
                        st.pyplot(fig)
                    else:
                        st.warning("Crop yield comparison needs valid crop names and numeric yield values.")
                else:
                    missing_msg = missing_fields_message(
                        {"Crop Name": crop_name_col, "Crop Yield/Production": crop_yield_col}
                    )
                    st.error(
                        f"Crop yield chart unavailable. Missing required mapping(s): {missing_msg}. "
                        "Check `Column Mapping Debug`."
                    )
                    st.info("Tip: choose the correct columns manually below.")
                    # Crop name candidates: low-cardinality object columns
                    name_opts = []
                    for c in filtered_df.columns:
                        try:
                            if filtered_df[c].dtype == "object" and filtered_df[c].nunique(dropna=True) <= 500:
                                name_opts.append(c)
                        except Exception:
                            continue
                    yield_opts = _numeric_candidate_columns(filtered_df)

                    c1, c2 = st.columns(2)
                    with c1:
                        picked_name = st.selectbox(
                            "Crop chart: pick crop/name column",
                            options=name_opts,
                            index=0 if name_opts else None,
                            key="manual_crop_name_col",
                        )
                    with c2:
                        picked_yield = st.selectbox(
                            "Crop chart: pick yield/production column",
                            options=yield_opts,
                            index=0 if yield_opts else None,
                            key="manual_crop_yield_col",
                        )
                    if picked_name and picked_yield:
                        try:
                            crop_plot_df = filtered_df[[picked_name, picked_yield]].copy()
                            crop_plot_df[picked_yield] = pd.to_numeric(crop_plot_df[picked_yield], errors="coerce")
                            crop_plot_df = crop_plot_df.dropna()
                            if not crop_plot_df.empty:
                                crop_compare = (
                                    crop_plot_df.groupby(picked_name, as_index=False)[picked_yield]
                                    .mean()
                                    .sort_values(picked_yield, ascending=False)
                                    .head(15)
                                )
                                fig, ax = plt.subplots(figsize=(10, 5))
                                ax.bar(crop_compare[picked_name].astype(str), crop_compare[picked_yield], label="Average yield")
                                ax.set_title("Crop Yield Comparison Across Crops (manual mapping)")
                                ax.set_xlabel(str(picked_name))
                                ax.set_ylabel(str(picked_yield))
                                ax.legend()
                                ax.tick_params(axis="x", rotation=45)
                                ax.grid(axis="y", alpha=0.3)
                                st.pyplot(fig)
                        except Exception as e:
                            st.warning(f"Could not render manual crop yield chart: {e}")

    with st.expander("🔗 Correlation Analysis (Rainfall vs Crop Yield)", expanded=False):
        st.caption("Merges standard rainfall and crop datasets by year and district/state to estimate correlation.")
        if st.button("Run Correlation Analysis", key="run_corr_analysis_btn"):
            try:
                rainfall_df = fetch_dataset_with_feedback(DATASETS["District-rainfall"], "District-rainfall")
                crop_df = fetch_dataset_with_feedback(
                    DATASETS["District Crop Production (1997)"], "District Crop Production (1997)"
                )

                if rainfall_df is None or crop_df is None:
                    st.warning("Insufficient source data for correlation analysis. Please try again later.")
                else:
                    rain_year_col, rain_value_col, rain_region_col = prepare_rainfall_columns(rainfall_df)
                    crop_year_col, _, crop_yield_col, crop_region_col = prepare_crop_columns(crop_df)

                    if not all([rain_year_col, rain_value_col, crop_year_col, crop_yield_col]):
                        missing_msg = missing_fields_message(
                            {
                                "Rainfall Year": rain_year_col,
                                "Rainfall Value": rain_value_col,
                                "Crop Year": crop_year_col,
                                "Crop Yield/Production": crop_yield_col,
                            }
                        )
                        st.error(
                            f"Correlation analysis unavailable. Missing required mapping(s): {missing_msg}. "
                            "Check `Column Mapping Debug`."
                        )
                    else:
                        rainfall_work = rainfall_df.copy()
                        crop_work = crop_df.copy()
                        rainfall_work[rain_year_col] = pd.to_numeric(rainfall_work[rain_year_col], errors="coerce")
                        rainfall_work[rain_value_col] = pd.to_numeric(rainfall_work[rain_value_col], errors="coerce")
                        crop_work[crop_year_col] = pd.to_numeric(crop_work[crop_year_col], errors="coerce")
                        crop_work[crop_yield_col] = pd.to_numeric(crop_work[crop_yield_col], errors="coerce")

                        if rain_region_col and crop_region_col:
                            rainfall_work[rain_region_col] = rainfall_work[rain_region_col].astype(str).str.strip().str.casefold()
                            crop_work[crop_region_col] = crop_work[crop_region_col].astype(str).str.strip().str.casefold()
                            rain_agg = rainfall_work.groupby([rain_year_col, rain_region_col], as_index=False)[rain_value_col].mean()
                            crop_agg = crop_work.groupby([crop_year_col, crop_region_col], as_index=False)[crop_yield_col].mean()
                            merged_corr = pd.merge(
                                rain_agg,
                                crop_agg,
                                left_on=[rain_year_col, rain_region_col],
                                right_on=[crop_year_col, crop_region_col],
                                how="inner",
                            )
                        else:
                            rain_agg = rainfall_work.groupby(rain_year_col, as_index=False)[rain_value_col].mean()
                            crop_agg = crop_work.groupby(crop_year_col, as_index=False)[crop_yield_col].mean()
                            merged_corr = pd.merge(
                                rain_agg,
                                crop_agg,
                                left_on=rain_year_col,
                                right_on=crop_year_col,
                                how="inner",
                            )

                        merged_corr = merged_corr[[rain_value_col, crop_yield_col]].dropna()
                        if len(merged_corr) < 3:
                            st.warning("Not enough merged records to calculate a reliable correlation.")
                        else:
                            corr_score = merged_corr[[rain_value_col, crop_yield_col]].corr().iloc[0, 1]
                            x_vals = merged_corr[rain_value_col].values
                            y_vals = merged_corr[crop_yield_col].values
                            line = linregress(x_vals, y_vals)
                            x_line = np.linspace(np.min(x_vals), np.max(x_vals), 100)
                            y_line = line.slope * x_line + line.intercept

                            fig, ax = plt.subplots(figsize=(8, 5))
                            ax.scatter(x_vals, y_vals, alpha=0.7, label="Observed points")
                            ax.plot(x_line, y_line, color="crimson", linestyle="--", label="Trend line")
                            ax.set_title("Rainfall vs Crop Yield Correlation")
                            ax.set_xlabel("Rainfall")
                            ax.set_ylabel("Crop Yield")
                            ax.legend()
                            ax.grid(alpha=0.25)
                            st.pyplot(fig)

                            st.metric("Pearson Correlation", f"{corr_score:.3f}")
                            st.write(f"Interpretation: **{correlation_interpretation(float(corr_score))}**")
            except Exception as analysis_err:
                st.warning(f"Could not complete correlation analysis: {analysis_err}")
        else:
            st.info("Click `Run Correlation Analysis` to fetch and merge source datasets on demand.")

    with st.expander("🤖 Rainfall Prediction (Linear Regression)", expanded=False):
        if filtered_df.empty:
            st.warning("No filtered data available for prediction.")
        else:
            pred_year_col, pred_rain_col, _ = prepare_rainfall_columns(filtered_df)
            if not pred_year_col or not pred_rain_col:
                missing_msg = missing_fields_message(
                    {"Rainfall Year": pred_year_col, "Rainfall Value": pred_rain_col}
                )
                st.error(
                    f"Prediction unavailable. Missing required mapping(s): {missing_msg}. "
                    "Check `Column Mapping Debug`."
                )
                st.info("Tip: choose the correct columns manually below.")
                manual_year_opts = []
                for c in filtered_df.columns:
                    c_norm = str(c).strip().lower()
                    if "year" in c_norm or c_norm in {"yr", "year"}:
                        manual_year_opts.append(c)
                manual_year_opts += _numeric_candidate_columns(filtered_df)
                manual_year_opts = list(dict.fromkeys(manual_year_opts))

                manual_val_opts = _numeric_candidate_columns(filtered_df)
                manual_val_opts = list(dict.fromkeys(manual_val_opts))

                c1, c2 = st.columns(2)
                with c1:
                    pred_year_col = st.selectbox(
                        "Prediction: pick year column",
                        options=manual_year_opts,
                        index=0 if manual_year_opts else None,
                        key="manual_pred_year_col",
                    )
                with c2:
                    pred_rain_col = st.selectbox(
                        "Prediction: pick rainfall/value column",
                        options=manual_val_opts,
                        index=0 if manual_val_opts else None,
                        key="manual_pred_rain_value_col",
                    )

                if not pred_year_col or not pred_rain_col:
                    st.stop()
            else:
                pred_df = filtered_df[[pred_year_col, pred_rain_col]].copy()
                pred_df[pred_year_col] = pd.to_numeric(pred_df[pred_year_col], errors="coerce")
                pred_df[pred_rain_col] = pd.to_numeric(pred_df[pred_rain_col], errors="coerce")
                pred_df = pred_df.dropna().sort_values(pred_year_col)
                yearly_rain = pred_df.groupby(pred_year_col, as_index=False)[pred_rain_col].mean()

                if len(yearly_rain) < 3:
                    st.warning("At least 3 yearly rainfall records are required to train the prediction model.")
                else:
                    model = LinearRegression()
                    X_train = yearly_rain[[pred_year_col]].values
                    y_train = yearly_rain[pred_rain_col].values
                    model.fit(X_train, y_train)

                    max_year = int(yearly_rain[pred_year_col].max())
                    future_years = np.array([max_year + 1, max_year + 2, max_year + 3]).reshape(-1, 1)
                    predictions = model.predict(future_years)

                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.plot(
                        yearly_rain[pred_year_col],
                        yearly_rain[pred_rain_col],
                        marker="o",
                        linestyle="-",
                        label="Historical rainfall",
                    )
                    ax.plot(
                        future_years.flatten(),
                        predictions,
                        marker="o",
                        linestyle="--",
                        color="orange",
                        label="Predicted rainfall",
                    )
                    ax.set_title("Historical and Predicted Rainfall")
                    ax.set_xlabel("Year")
                    ax.set_ylabel("Rainfall")
                    ax.legend()
                    ax.grid(alpha=0.3)
                    st.pyplot(fig)

                    metric_cols = st.columns(3)
                    for idx, year in enumerate(future_years.flatten()):
                        metric_cols[idx].metric(f"Predicted Rainfall ({int(year)})", f"{predictions[idx]:.2f}")
                    st.caption("Prediction based on linear trend of historical data. Actual values may vary.")

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
            df2, _, compare_err = fetch_from_api(compare_id)

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
            render_fetch_error(compare_err, context=f"Fetching comparison dataset `{compare_choice}`")

elif "df" in st.session_state and (st.session_state["df"] is None or st.session_state["df"].empty):
    # Fetch happened but returned no data; show details if available
    err = st.session_state.get("last_fetch_error")
    if err:
        render_fetch_error(err, context=f"Fetching `{selected_dataset}`")
    else:
        st.info("No data loaded yet. Click `Fetch Data` to load the selected dataset.")

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.caption("Powered by data.gov.in | Built with ❤️ using Streamlit")
