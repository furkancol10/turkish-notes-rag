"""İş mantığı (arayüzden bağımsız): app.py'deki yardımcıların masaüstü karşılığı."""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from src import config, settings
from src.embedder import _model
from src.conversation import fit_budget, window
from src.generator import answer, answer_followup, answer_meta
from src.rewriter import condense
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


def _fail_llm(e):
    return AskError("ollama" if is_connection_error(e) else "other", f"Cevap üretilemedi: {e}")


def last_sources(messages) -> list[dict]:
    """Son asistan mesajının kayıtlı kaynakları (takip sorusu bunlarla cevaplanır)."""
    for m in reversed(messages or []):
        if m.get("role") == "assistant":
            return [s for s in (m.get("sources") or []) if isinstance(s, dict)]
    return []


def _as_results(sources):
    """Kayıtlı kaynak sözlüklerini (parça, skor) çiftlerine çevirir (arayüz bu biçimi bekler)."""
    return [(SimpleNamespace(source=s.get("source", ""), heading=s.get("heading", ""),
                             page=s.get("page"), text=s.get("text", "")),
             float(s.get("score", 0.0) or 0.0)) for s in sources]


def ask(question: str, top_k: int, backend: str, prior_messages=None):
    """Tüm hat: pencere -> yönlendir -> (yeniden yaz -> getir -> bütçele) -> üret.
    (cevap, sonuçlar, info) döner; info = {"route", "query"}. Hata olursa AskError fırlatır."""
    history = window(prior_messages or [])
    r = route(question, bool(history))
    info = {"route": r, "query": None}
    if r == "meta":                    # asistanla ilgili soru: arama yok, kaynak yok
        try:
            return answer_meta(question), [], info
        except Exception as e:
            raise _fail_llm(e)
    src = last_sources(prior_messages) if r == "followup" else []
    if r == "followup" and not src:    # dayanacak kaynak yok (ör. önceki cevap meta): normal aramaya düş
        r = info["route"] = "notes"
    if r == "followup":                # önceki cevabın kaynaklarıyla cevapla, yeni arama yok
        try:
            return answer_followup(question, history, src), _as_results(src), info
        except Exception as e:
            raise _fail_llm(e)
    if backend == "numpy" and index_status() is None:
        raise AskError("index", "İndeks bulunamadı.")
    query = question
    if history:
        try:
            query = condense(question, history) or question
        except Exception as e:
            raise _fail_llm(e)
    info["query"] = query
    try:
        load_embed_model()
        results = retrieve(query, k=top_k, backend=backend)
    except Exception as e:
        raise AskError("index" if is_index_missing(e) else "other", f"Arama başarısız: {e}")
    history, results = fit_budget(history, results, question)
    try:
        return answer(question, results, history), results, info
    except Exception as e:
        raise _fail_llm(e)


def example_questions():
    from src.examples import example_questions as _eq
    try:
        return _eq(settings.notes_dir())
    except Exception:
        return []
