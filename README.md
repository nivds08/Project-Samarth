# 🪶 Manthana — AI-Powered Q&A System for Bharat

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
- **Backend:** Python  
- **Libraries:** Pandas, NumPy, OpenAI API / LangChain  
- **Data Sources:** Government Open Data Platform (data.gov.in)  

---

## 🏗️ System Architecture
1. User enters a query in plain English or Hindi.  
2. The system parses the query and maps it to relevant dataset columns.  
3. AI module extracts relevant data and formulates an answer.  
4. The response is displayed along with related insights or graphs.  

---

## 💻 Installation
```bash
git clone https://github.com/nivds08/Project-Samarth
cd project-samarth
pip install -r requirements.txt
streamlit run app.py
