"""Sohbet arayüzü:  uv run streamlit run app.py"""
from datetime import datetime

import streamlit as st

from src import config
from src.chunker import chunk_docs
from src.embedder import _model, embed_passages
from src.generator import answer
from src.index import get_index, index_name
from src.loader import load_notes
from src.retriever import retrieve

st.set_page_config(page_title="Kişisel Not Arama", page_icon="📝")


@st.cache_resource(show_spinner="Embedding modeli yükleniyor...")
def load_embed_model():
    """Modeli bir kez yükle; sonraki sorularda yeniden yüklenmez."""
    return _model(config.EMBED_MODEL)


def index_status():
    """(son indeksleme zamanı | None) — numpy indeksinin dosya tarihinden."""
    f = config.INDEX_DIR / "numpy" / index_name(
        config.EMBED_MODEL, config.CHUNK_STRATEGY, config.CHUNK_SIZE) / "vecs.npy"
    return datetime.fromtimestamp(f.stat().st_mtime) if f.exists() else None


def reindex():
    docs = load_notes()
    chunks = chunk_docs(docs)
    vecs = embed_passages([c.text for c in chunks])
    name = index_name(config.EMBED_MODEL, config.CHUNK_STRATEGY, config.CHUNK_SIZE)
    for backend in ("numpy", "chroma"):
        get_index(backend, name).build(chunks, vecs)
    return len(docs), len(chunks)


def is_connection_error(e: Exception) -> bool:
    return isinstance(e, ConnectionError) or "connect" in str(e).lower()


# ---------------- Kenar çubuğu ----------------
config.NOTES_DIR.mkdir(parents=True, exist_ok=True)
with st.sidebar:
    st.header("Notlar")
    notes = sorted(p for p in config.NOTES_DIR.iterdir() if p.suffix in (".md", ".txt"))
    with st.expander(f"{len(notes)} not"):
        for p in notes:
            st.text(p.name)
    uploads = st.file_uploader("Not yükle (.md / .txt)", type=["md", "txt"],
                               accept_multiple_files=True)
    if uploads and st.button("Yüklenenleri kaydet"):
        for u in uploads:
            (config.NOTES_DIR / u.name).write_bytes(u.getvalue())
        st.success(f"{len(uploads)} dosya kaydedildi. Şimdi yeniden indeksle.")

    st.header("İndeks")
    if st.button("Yeniden indeksle"):
        with st.spinner("İndeksleniyor (not okuma, parçalama, embed)..."):
            n_docs, n_chunks = reindex()
        st.success(f"{n_docs} not → {n_chunks} parça")
    ts = index_status()
    st.caption(f"Model: {config.EMBED_MODEL}  \nParça boyutu: {config.CHUNK_SIZE} karakter  \n"
               f"Son indeksleme: {ts:%Y-%m-%d %H:%M}" if ts else
               "Henüz indeks yok. 'Yeniden indeksle'ye bas.")

    st.header("Ayarlar")
    top_k = st.slider("Kaç parça getirilsin (top_k)", 1, 10, config.TOP_K)
    backend = st.radio("İndeks yöntemi", ["numpy", "chroma"],
                       index=["numpy", "chroma"].index(config.INDEX_BACKEND), horizontal=True)
    if st.button("Sohbeti temizle"):
        st.session_state.msgs = []
        st.rerun()

# ---------------- Sohbet ----------------
st.title("Kişisel Not Arama")
st.caption("Notlarına soru sor; cevap sadece notlarındaki bilgiye dayanır.")


def show_sources(results):
    with st.expander("Kaynaklar"):
        for i, (c, s) in enumerate(results, 1):
            with st.expander(f"[{i}] {c.source} / {c.heading}  (skor {s:.2f})"):
                st.text(c.text)


st.session_state.setdefault("msgs", [])  # (rol, metin, kaynaklar)
for role, text, results in st.session_state.msgs:
    with st.chat_message(role):
        st.write(text)
        if results:
            show_sources(results)

if q := st.chat_input("Notlarına bir soru sor"):
    st.session_state.msgs.append(("user", q, None))
    with st.chat_message("user"):
        st.write(q)
    with st.chat_message("assistant"):
        if index_status() is None and backend == "numpy":
            st.error("İndeks bulunamadı. Soldan 'Yeniden indeksle'ye bas.")
            st.stop()
        try:
            with st.spinner("Notlarda aranıyor..."):
                load_embed_model()
                results = retrieve(q, k=top_k, backend=backend)
        except Exception:
            st.error("İndeks bulunamadı. Soldan 'Yeniden indeksle'ye bas.")
            st.stop()
        try:
            with st.spinner("Cevap üretiliyor..."):
                ans = answer(q, results)
        except Exception as e:
            if is_connection_error(e):
                st.error("Ollama'ya bağlanılamadı. ollama servisini başlat "
                         "(`ollama serve`) ve tekrar dene.")
            else:
                st.error(f"Cevap üretilemedi: {e}")
            st.stop()
        st.write(ans)
        show_sources(results)
    st.session_state.msgs.append(("assistant", ans, results))
