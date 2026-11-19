"""Minimal sohbet arayüzü:  uv run streamlit run app.py"""
import streamlit as st

from src.generator import answer
from src.retriever import retrieve

st.title("Kişisel Not Arama (naive RAG)")
if "msgs" not in st.session_state:
    st.session_state.msgs = []
for role, text, sources in st.session_state.msgs:
    with st.chat_message(role):
        st.write(text)
        if sources:
            with st.expander("Kaynaklar"):
                st.markdown(sources)

if q := st.chat_input("Notlarına bir soru sor"):
    st.session_state.msgs.append(("user", q, ""))
    with st.chat_message("user"):
        st.write(q)
    results = retrieve(q)
    ans = answer(q, results)
    src = "\n\n".join(f"**[{i}] {c.source}** / {c.heading} (skor {s:.2f})\n\n> {c.text[:300]}..."
                      for i, (c, s) in enumerate(results, 1))
    st.session_state.msgs.append(("assistant", ans, src))
    with st.chat_message("assistant"):
        st.write(ans)
        with st.expander("Kaynaklar"):
            st.markdown(src)
