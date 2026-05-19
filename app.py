import streamlit as st
from rag import ask_db

st.set_page_config(page_title="📊 AI Assistant", layout="wide")

st.title("📊 AI Assistant")

if "history" not in st.session_state:
    st.session_state.history = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render past messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            st.subheader("🧠 Generated SQL")
            st.code(msg["sql"], language="sql")
            st.subheader("📊 Data")
            st.dataframe(msg["data"])
            st.subheader("📌 Insight")
            st.write(msg["answer"])
        else:
            st.write(msg["content"])

if question := st.chat_input("Apa yang ingin kamu tanyakan?"):
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = ask_db(question, st.session_state.history)

        if result.get("error"):
            st.error(result["error"])
        else:
            st.subheader("🧠 Generated SQL")
            st.code(result["sql"], language="sql")
            st.subheader("📊 Data")
            st.dataframe(result["data"])
            st.subheader("📌 Insight")
            st.write(result["answer"])

    st.session_state.messages.append({"role": "user", "content": question})
    if not result.get("error"):
        st.session_state.messages.append({
            "role": "assistant",
            "sql": result["sql"],
            "data": result["data"],
            "answer": result["answer"],
        })