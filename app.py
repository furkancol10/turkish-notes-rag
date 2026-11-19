"""Sohbet arayüzü:  uv run streamlit run app.py"""
from datetime import datetime
from pathlib import Path

import streamlit as st

from src import config, settings
from src.chunker import chunk_docs
from src.embedder import _model, embed_passages
from src.generator import answer, answer_meta
from src.index import get_index, index_name
from src.loader import list_note_files, load_notes, newest_mtime, rel_source
from src.notes_io import save_note
from src.retriever import retrieve
from src.router import route

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
    if not docs:
        raise ValueError("Bu klasörde .md/.txt not bulunamadı.")
    chunks = chunk_docs(docs)
    vecs = embed_passages([c.text for c in chunks])
    name = index_name(config.EMBED_MODEL, config.CHUNK_STRATEGY, config.CHUNK_SIZE)
    for backend in ("numpy", "chroma"):
        get_index(backend, name).build(chunks, vecs)
    return len(docs), len(chunks)


save_upload = save_note


def is_index_missing(e: Exception) -> bool:
    return isinstance(e, FileNotFoundError) or "does not exist" in str(e).lower()


def is_connection_error(e: Exception) -> bool:
    return isinstance(e, ConnectionError) or "connect" in str(e).lower()


# ---------------- Kenar çubuğu ----------------
with st.sidebar:
    st.header("Not klasörü")
    folder_in = st.text_input("Klasör yolu", value=str(settings.notes_dir()))
    c1, c2 = st.columns(2)
    if c1.button("Uygula"):
        try:
            settings.set_notes_dir(folder_in)
            st.rerun()
        except ValueError as e:
            st.error(str(e))
    if c2.button("Örnek notlar"):
        settings.reset_notes_dir()
        st.rerun()

    st.header("Notlar")
    _dir = settings.notes_dir()
    notes = [rel_source(p, _dir) for p in list_note_files(_dir)]
    if not notes:
        st.info("Bu klasörde .md/.txt not yok.")
    with st.expander(f"{len(notes)} not"):
        for p in notes:
            st.text(p)
    uploads = st.file_uploader("Not yükle (.md / .txt)", type=["md", "txt"],
                               accept_multiple_files=True)
    if uploads and st.button("Yüklenenleri kaydet"):
        saved = [save_upload(u.name, u.getvalue()) for u in uploads]
        n_ok = sum(1 for x in saved if x)
        if n_ok:
            st.success(f"{n_ok} dosya kaydedildi. Şimdi yeniden indeksle.")
        if n_ok < len(saved):
            st.warning("Geçersiz dosya adı atlandı.")

    st.header("İndeks")
    if st.button("Yeniden indeksle"):
        try:
            with st.spinner("İndeksleniyor (not okuma, parçalama, embed)..."):
                n_docs, n_chunks = reindex()
            st.success(f"{n_docs} not → {n_chunks} parça")
        except ValueError as e:
            st.warning(str(e))
    ts = index_status()
    _newest = newest_mtime(_dir)
    if ts and _newest and _newest > ts.timestamp():
        st.warning("Notlar değişti, yeniden indeksle.")
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
        if route(q) == "meta":          # asistanla ilgili soru: arama yok, kaynak yok
            try:
                with st.spinner("Cevap üretiliyor..."):
                    ans = answer_meta(q)
            except Exception as e:
                st.error("Ollama'ya bağlanılamadı." if is_connection_error(e) else f"Cevap üretilemedi: {e}")
                st.stop()
            st.write(ans)
            st.session_state.msgs.append(("assistant", ans, []))
            st.stop()
        if index_status() is None and backend == "numpy":
            st.error("İndeks bulunamadı. Soldan 'Yeniden indeksle'ye bas.")
            st.stop()
        try:
            with st.spinner("Notlarda aranıyor..."):
                load_embed_model()
                results = retrieve(q, k=top_k, backend=backend)
        except Exception as e:
            if is_index_missing(e):
                st.error("İndeks bulunamadı. Soldan 'Yeniden indeksle'ye bas.")
            else:
                st.error(f"Arama başarısız: {e}")
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
