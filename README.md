# 🪶 Manthana — AI-Powered Q&A System

*"Churning government data to extract the required insights."*

---

## 📖 Overview
**Manthana** is an AI-powered Q&A system that parses and understands **Indian government datasets** to answer user queries in natural language.  
Inspired by the Sanskrit word *Manthana* — meaning *churning* — this system extracts valuable insights from vast data sources, making open government data more **accessible, interpretable, and interactive**.

---

## ⚙️ Features
- 🧠 Natural Language Question Answering  
- 📊 Data parsing and cleaning from government datasets  
- 🔍 Semantic search and intelligent retrieval  
- 🗣️ Context-aware answers with citation mapping  
- 🌐 Scalable backend for multiple datasets  

---

## 🧩 Tech Stack
- **Frontend:** Streamlit  
- **Backend:** Python  (for data handling and logic)
- **Libraries:** Pandas, dotenv, requests  
- **Data Sources:** Government Open Data Platform (data.gov.in)  

---

## 🏗️ System Architecture
1. User selects a required dataset.  
2. The system fetches that dataset and allows the user to filter out the required data.  
3. AI module extracts relevant data and formulates a suitable output.  
4. The system also allows the user to compare one dataset with another datasets to find required answers.

---

## 💻 Installation
```bash
git clone https://github.com/nivds08/Project-Samarth
cd project-samarth
pip install -r requirements.txt
streamlit run app.py
