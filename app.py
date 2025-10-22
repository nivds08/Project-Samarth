# app.py

import sys
import os
import streamlit as st
import matplotlib.pyplot as plt

# Add src folder to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from data_handler.fetch_manager import get_dataset
from data_handler.preprocessor import preprocess
from query_engine.executor import compare_states

# 1️⃣ Load and preprocess rainfall data
rainfall_df = get_dataset("rainfall")
rainfall_df = preprocess(rainfall_df, "rainfall")

if rainfall_df is None or rainfall_df.empty:
    st.error("No rainfall data available!")
    st.stop()

# 2️⃣ Sidebar: user input
st.sidebar.title("Rainfall Comparison")

# Handle missing 'state' gracefully
if 'state' not in rainfall_df.columns:
    st.error("The dataset does not have a 'state' column.")
    st.stop()

states = rainfall_df['state'].unique()
state1 = st.sidebar.selectbox("Select State 1", states)
state2 = st.sidebar.selectbox("Select State 2", states)

years = sorted(rainfall_df['year'].dropna().unique())
years = [None] + list(years)  # None for "All Years"
selected_year = st.sidebar.selectbox("Select Year", years, format_func=lambda x: "All Years" if x is None else int(x))

# 3️⃣ Run query
result_df = compare_states(rainfall_df, state1, state2, year=selected_year)

# 4️⃣ Display results
st.title("Rainfall Comparison")
st.write(f"Comparison between **{state1}** and **{state2}**", 
         f"{'for year ' + str(selected_year) if selected_year else 'over all years'}")

if result_df is not None and not result_df.empty:
    st.dataframe(result_df)

    # 5️⃣ Plot bar chart
    plt.figure(figsize=(6,4))
    plt.bar(result_df['state'], result_df['average_rainfall_mm'], color=['skyblue','orange'])
    plt.ylabel("Average Rainfall (mm)")
    plt.title("Rainfall Comparison")
    st.pyplot(plt)
else:
    st.warning("No data available for the selected states/year.")
