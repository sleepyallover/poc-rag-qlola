import streamlit as st
from rag import ask_db

st.set_page_config(page_title="📊 AI Assistant", layout="wide")

st.title("📊 AI Assistant")

# 👇 CACHE DI SINI
@st.cache_data(show_spinner=False)
def cached_ask(question):
    return ask_db(question)

question = st.text_input("Apa yang ingin kamu tanyakan?")

if st.button("Tanyakan"):
    if question:
        with st.spinner("Thinking..."):
            result = cached_ask(question)  # pake cache

        if result.get("error"):
            st.error(result["error"])
        else:
            st.subheader("🧠 Generated SQL")
            st.code(result["sql"], language="sql")

            st.subheader("📊 Data")
            st.dataframe(result["data"])

            st.subheader("📌 Insight")
            st.write(result["answer"])