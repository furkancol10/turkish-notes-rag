"""İş mantığı (arayüzden bağımsız): app.py'deki yardımcıların masaüstü karşılığı."""
from datetime import datetime
from pathlib import Path

from src import config, settings
from src.embedder import _model
from src.generator import answer, answer_meta
from src.index import index_name
from src.loader import list_note_files, newest_mtime, rel_source
from src.pipeline import build_index
from src.notes_io import save_note
from src.retriever import retrieve
from src.router import route


def load_embed_model():
    """Modeli bir kez yükler (lru_cache), sonraki çağrılar anında döner."""
    return _model(config.EMBED_MODEL)


def notes_dir() -> Path:
    return settings.notes_dir()


def list_notes() -> list[str]:
    """Notların klasöre göre göreli yolları (alt klasörler dahil)."""
    d = settings.notes_dir()
    return [rel_source(p, d) for p in list_note_files(d)]


def folder_problem():
    """Etkin klasörle ilgili kullanıcıya gösterilecek sorun metni veya None."""
    d = settings.notes_dir()
    try:
        settings.validate_dir(d)
    except ValueError as e:
        return str(e)
    return None


def notes_changed() -> bool:
    """Notlardan en yenisi indeksten sonra değiştiyse True."""
    ts, newest = index_status(), newest_mtime()
    return bool(ts and newest and newest > ts.timestamp())


def set_folder(path) -> str:
    return str(settings.set_notes_dir(path))


def reset_folder():
    settings.reset_notes_dir()


def index_status():
    """Son indeksleme zamanı (numpy indeksinin dosya tarihi) veya None."""
    f = config.INDEX_DIR / "numpy" / index_name(
        config.EMBED_MODEL, config.CHUNK_STRATEGY, config.CHUNK_SIZE) / "vecs.npy"
    return datetime.fromtimestamp(f.stat().st_mtime) if f.exists() else None


def reindex():
    return build_index()


def import_note(src_path: str):
    """Dosyayı not klasörüne temizlenmiş adla kopyalar; kaydedilen adı döner, geçersizse None."""
    return save_note(src_path, Path(src_path).read_bytes())


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
    if route(question) == "meta":      # asistanla ilgili soru: arama yok, kaynak yok
        try:
            return answer_meta(question), []
        except Exception as e:
            raise AskError("ollama" if is_connection_error(e) else "other",
                           f"Cevap üretilemedi: {e}")
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


def example_questions():
    from src.examples import example_questions as _eq
    try:
        return _eq(settings.notes_dir())
    except Exception:
        return []
