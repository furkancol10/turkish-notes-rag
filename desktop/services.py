"""İş mantığı (arayüzden bağımsız): app.py'deki yardımcıların masaüstü karşılığı."""
from datetime import datetime
from pathlib import Path

from src import config
from src.chunker import chunk_docs
from src.embedder import _model, embed_passages
from src.generator import answer
from src.index import get_index, index_name
from src.loader import load_notes
from src.retriever import retrieve


def load_embed_model():
    """Modeli bir kez yükler (lru_cache), sonraki çağrılar anında döner."""
    return _model(config.EMBED_MODEL)


def list_notes() -> list[Path]:
    config.NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(p for p in config.NOTES_DIR.iterdir() if p.suffix in (".md", ".txt"))


def index_status():
    """Son indeksleme zamanı (numpy indeksinin dosya tarihi) veya None."""
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


def import_note(src_path: str):
    """Dosyayı NOTES_DIR'e temizlenmiş adla kopyalar (path traversal yok).
    Kaydedilen adı döner, geçersizse None."""
    safe = Path(src_path.replace("\\", "/")).name.strip()
    if not safe or safe.startswith(".") or Path(safe).suffix.lower() not in (".md", ".txt"):
        return None
    config.NOTES_DIR.mkdir(parents=True, exist_ok=True)
    (config.NOTES_DIR / safe).write_bytes(Path(src_path).read_bytes())
    return safe


def is_index_missing(e: Exception) -> bool:
    return isinstance(e, FileNotFoundError) or "does not exist" in str(e).lower()


def is_connection_error(e: Exception) -> bool:
    return isinstance(e, ConnectionError) or "connect" in str(e).lower()


class AskError(Exception):
    """kind: 'index' | 'ollama' | 'other'"""
    def __init__(self, kind: str, msg: str):
        super().__init__(msg)
        self.kind = kind


def ask(question: str, top_k: int, backend: str):
    """Arama + LLM cevabı. (cevap, sonuçlar) döner; hata olursa AskError fırlatır."""
    if backend == "numpy" and index_status() is None:
        raise AskError("index", "İndeks bulunamadı.")
    try:
        load_embed_model()
        results = retrieve(question, k=top_k, backend=backend)
    except Exception as e:
        raise AskError("index" if is_index_missing(e) else "other", f"Arama başarısız: {e}")
    try:
        return answer(question, results), results
    except Exception as e:
        raise AskError("ollama" if is_connection_error(e) else "other",
                       f"Cevap üretilemedi: {e}")
