"""Sohbet arayüzü:  uv run streamlit run app.py"""
from datetime import datetime
from pathlib import Path

import streamlit as st

from src import config, history, settings
from desktop import services
from src.embedder import _model
from src.formats import LABEL_TEXT, NO_NOTES_MSG, UPLOAD_TYPES
from src.index import index_name
from src.loader import list_note_files, newest_mtime, rel_source
from src.pipeline import build_index
from src.notes_io import save_note

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
    return build_index()


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
        st.info(NO_NOTES_MSG)
    with st.expander(f"{len(notes)} not"):
        for p in notes:
            st.text(p)
    uploads = st.file_uploader(f"Not yükle ({LABEL_TEXT})", type=UPLOAD_TYPES,
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
                res = reindex()
            st.success(res.summary())
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
    top_k = st.slider("Kaç parça getirilsin (top_k)", 1, 15, config.TOP_K)
    backend = st.radio("İndeks yöntemi", ["numpy", "chroma"],
                       index=["numpy", "chroma"].index(config.INDEX_BACKEND), horizontal=True)
    th_on = st.checkbox("Düşük benzerlikte 'notlarda yok' de", settings.get_threshold_enabled())
    th = st.slider("Cevap eşiği", 0.20, 0.90, float(min(0.90, max(0.20, settings.get_score_threshold()))), 0.01,
                   help="Yüksek: daha çok 'notlarda yok', düşük: daha çok cevap denemesi")
    if st.button("Sohbeti temizle"):
        st.session_state.msgs = []
        st.rerun()

# ---------------- Sohbet ----------------
st.title("Kişisel Not Arama")
st.caption("Notlarına soru sor; cevap sadece notlarındaki bilgiye dayanır.")


def show_sources(sources):
    with st.expander("Kaynaklar"):
        for i, src in enumerate(sources, 1):
            page = f", s.{src['page']}" if src.get("page") else ""
            head = f" > {src['heading']}" if src.get("heading") else ""
            with st.expander(f"[{i}] {src['source']}{head}{page}  (skor {src['score']:.2f})"):
                st.text(src["text"])


def show_msg(m):
    st.write(m["text"])
    if m.get("query"):
        st.caption(f"Aranan: {m['query']}")
    if m.get("note"):
        st.caption(m["note"])
    if m.get("sources"):
        show_sources(m["sources"])


st.session_state.setdefault("msgs", [])  # history.py biçimi: {role, text, sources, query?}
for m in st.session_state.msgs:
    with st.chat_message(m["role"]):
        show_msg(m)

if q := st.chat_input("Notlarına bir soru sor"):
    prior = list(st.session_state.msgs)       # bu sorudan önceki mesajlar (hafıza)
    st.session_state.msgs.append({"role": "user", "text": q, "sources": []})
    with st.chat_message("user"):
        st.write(q)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Notlarda aranıyor ve cevap üretiliyor..."):
                ans, results, info = services.ask(q, top_k, backend, prior, th, th_on)
        except services.AskError as e:
            if e.kind == "index":
                st.error("İndeks bulunamadı. Soldan 'Yeniden indeksle'ye bas.")
            elif e.kind == "ollama":
                st.error("Ollama'ya bağlanılamadı. ollama servisini başlat "
                         "(`ollama serve`) ve tekrar dene.")
            else:
                st.error(str(e))
            st.stop()
        query = info.get("query")
        msg = {"role": "assistant", "text": ans, "sources": history.sources_from_results(results),
               "intent": info.get("intent", "notes")}
        for k in ("below_threshold", "top_score", "threshold", "note"):
            if k in info:
                msg[k] = info[k]
        if query and query != q:
            msg["query"] = query
        show_msg(msg)
    st.session_state.msgs.append(msg)
