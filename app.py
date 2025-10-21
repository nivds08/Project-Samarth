# app.py

import sys
import os

# Add the 'src' folder to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st
from data_handler.fetch_manager import get_dataset
from data_handler.preprocessor import preprocess
from query_engine.executor import compare_states

import matplotlib.pyplot as plt

# 1️⃣ Load and preprocess data
rainfall_df = get_dataset("rainfall")
rainfall_df = preprocess(rainfall_df, "rainfall")

# 2️⃣ Sidebar: user input
st.sidebar.title("Rainfall Comparison")
states = rainfall_df['state'].unique()
state1 = st.sidebar.selectbox("Select State 1", states)
state2 = st.sidebar.selectbox("Select State 2", states)

years = sorted(rainfall_df['year'].unique())
years.insert(0, "All")  # option for all years
selected_year = st.sidebar.selectbox("Select Year", years)

# 3️⃣ Filter year
if selected_year == "All":
    year_value = None
else:
    year_value = int(selected_year)

# 4️⃣ Run query
result_df = compare_states(rainfall_df, state1, state2, year=year_value)

# 5️⃣ Display result
st.title("Rainfall Comparison")
st.write(f"Comparison between **{state1}** and **{state2}**", 
         f"{'for year ' + str(year_value) if year_value else 'over all years'}")
st.dataframe(result_df)

# 6️⃣ Plot bar chart
if result_df is not None and not result_df.empty:
    plt.bar(result_df['state'], result_df['average_rainfall_mm'], color=['skyblue','orange'])
    plt.ylabel("Average Rainfall (mm)")
    plt.title("Rainfall Comparison")
    st.pyplot(plt)
