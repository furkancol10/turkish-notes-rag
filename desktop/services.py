"""İş mantığı (arayüzden bağımsız): app.py'deki yardımcıların masaüstü karşılığı."""
from pathlib import Path

from src import config, qa, settings
from src.index import NumpyIndex, index_name
from src.loader import list_note_files, newest_mtime, rel_source
from src.pipeline import build_index
from src.notes_io import save_note


load_embed_model = qa.load_embed_model


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
    if bool(ts and newest and newest > ts.timestamp()):
        return True
    if ts:  # silinen/eklenen not: indeksteki kaynaklar klasörle uyuşmuyor
        try:
            name = index_name(config.EMBED_MODEL, config.CHUNK_STRATEGY, config.CHUNK_SIZE)
            return set(NumpyIndex(name).doc_titles()) != set(list_notes())
        except Exception:
            return False
    return False


def set_folder(path) -> str:
    return str(settings.set_notes_dir(path))


def reset_folder():
    settings.reset_notes_dir()


index_status = qa.index_status


def reindex():
    return build_index()


def import_note(src_path: str):
    """Dosyayı not klasörüne temizlenmiş adla kopyalar; kaydedilen adı döner, geçersizse None."""
    return save_note(src_path, Path(src_path).read_bytes())


is_index_missing = qa.is_index_missing
is_connection_error = qa.is_connection_error
AskError = qa.AskError
last_sources = qa.last_sources
last_assistant_text = qa.last_assistant_text
cited_sources = qa.cited_sources


def ask(question: str, top_k: int, backend: str, prior_messages=None,
        threshold=None, threshold_enabled=None):
    """Ortak hat (src/qa.py) için ince sarmalayıcı; (cevap, sonuçlar, info) döner."""
    return qa.ask(question, top_k=top_k, backend=backend, prior_messages=prior_messages,
                  threshold=threshold, threshold_enabled=threshold_enabled)


def example_questions():
    from src.examples import example_questions as _eq
    try:
        return _eq(settings.notes_dir())
    except Exception:
        return []
