import sys
import os
import re
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# ------------------------------------------------------------
# 1️⃣ Setup paths and imports
# ------------------------------------------------------------
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.data_handler.fetch_manager import fetch_from_api
from src.query_engine.executor import compare_states

# ------------------------------------------------------------
# 2️⃣ Load environment variables
# ------------------------------------------------------------
load_dotenv()

# ------------------------------------------------------------
# 3️⃣ Define dataset resource IDs
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# 4️⃣ Streamlit UI setup
# ------------------------------------------------------------
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
selected_dataset = st.selectbox("Choose a dataset:", list(DATASETS.keys()))

# ------------------------------------------------------------
# 5️⃣ Fetch Data Button
# ------------------------------------------------------------
if st.button("Fetch Data", key="fetch_btn"):
    resource_id = DATASETS[selected_dataset]
    with st.spinner(f"Fetching data for **{selected_dataset}**..."):
        df, col_suggestions = fetch_from_api(resource_id)

    if df is not None and not df.empty:
        st.session_state.df = df
        st.success(f"✅ Successfully fetched {len(df)} records!")

        # Column info
        st.markdown("### 🔹 Column Summary")
        if isinstance(col_suggestions, dict):
            for col, info in col_suggestions.items():
                st.write(f"**{col}** — dtype: {info['dtype']}, unique: {info['num_unique']}, missing: {info['num_missing']}")
                st.caption(f"Sample values: {info['sample_values']}")
        else:
            st.warning("⚠️ Column details unavailable.")

        # Show data preview
        st.dataframe(df.head(20))

        # Manual query input
        st.markdown("### 🧠 Manual Query")
        user_query = st.text_input("Type your question or filter requirement here:")
        if st.button("Run Query", key="query_btn"):
            query = user_query.strip().lower()
            if not query:
                st.warning("Please enter a query first.")
            else:
                filtered_df = df.copy()

                try:
                    # 1️⃣ Year filter
                    years = re.findall(r"\b(19\d{2}|20\d{2})\b", query)
                    if "between" in query and len(years) >= 2:
                        y1, y2 = sorted(map(int, years[:2]))
                        year_cols = [c for c in df.columns if "year" in c.lower()]
                        for col in year_cols:
                            filtered_df = filtered_df[(filtered_df[col] >= y1) & (filtered_df[col] <= y2)]
                    elif years:
                        y = years[0]
                        year_cols = [c for c in df.columns if "year" in c.lower()]
                        for col in year_cols:
                            filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(y)]

                    # 2️⃣ Month filter
                    months = [
                        "january","february","march","april","may","june",
                        "july","august","september","october","november","december",
                        "jan","feb","mar","apr","jun","jul","aug","sep","sept","oct","nov","dec"
                    ]
                    found_months = [m for m in months if m in query]
                    if found_months:
                        month_cols = [c for c in df.columns if "month" in c.lower()]
                        for m in found_months:
                            for col in month_cols:
                                filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(m[:3], case=False, na=False)]

                    # 3️⃣ State / district / region filters
                    geo_cols = [c for c in df.columns if any(x in c.lower() for x in ["state", "district", "region", "sub-division"])]
                    for col in geo_cols:
                        for word in query.split():
                            filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(word, case=False, na=False)]

                    # 4️⃣ Crop filter
                    crop_cols = [c for c in df.columns if "crop" in c.lower()]
                    if crop_cols:
                        for word in query.split():
                            for col in crop_cols:
                                filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(word, case=False, na=False)]

                    # 5️⃣ General fallback
                    if filtered_df.equals(df):
                        matches = pd.Series(False, index=df.index)
                        for word in query.split():
                            for col in df.columns:
                                matches |= df[col].astype(str).str.contains(word, case=False, na=False)
                        filtered_df = df[matches]

                    # 6️⃣ Show results
                    if filtered_df.empty:
                        st.warning("⚠️ No matching records found.")
                    else:
                        st.success(f"✅ Found {len(filtered_df)} matching records.")
                        st.dataframe(filtered_df)

                except Exception as e:
                    st.error(f"Error processing query: {e}")

        # Optional comparison
        st.markdown("### 🔍 Compare with Another Dataset (Optional)")
        compare_choice = st.selectbox("Select another dataset to compare:", ["None"] + list(DATASETS.keys()), key="compare_box")
        if compare_choice != "None":
            compare_id = DATASETS[compare_choice]
            with st.spinner(f"Fetching comparison dataset: {compare_choice}..."):
                df2, _ = fetch_from_api(compare_id)
            if df2 is not None and not df2.empty:
                st.info(f"Comparing **{selected_dataset}** and **{compare_choice}** ...")
                try:
                    comparison_result = compare_states(df, df2)
                    st.dataframe(comparison_result)
                except Exception as e:
                    st.error(f"Error during comparison: {e}")
            else:
                st.error("❌ Could not fetch comparison dataset.")
    else:
        st.error("❌ Failed to fetch data. Please check the resource ID or API limit.")

# ------------------------------------------------------------
# 6️⃣ Footer
# ------------------------------------------------------------
st.markdown("---")
st.caption("Powered by data.gov.in | Built with ❤️ using Streamlit")
