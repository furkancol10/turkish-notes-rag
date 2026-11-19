"""İş mantığı (arayüzden bağımsız): app.py'deki yardımcıların masaüstü karşılığı."""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from src import config, history as _hist, settings
from src.embedder import _model
from src.conversation import fit_budget, window
from src.generator import answer, answer_followup, answer_meta
from src.rewriter import analyze
from src.sources import answer_sources, cited_indices
from src.formats import NOT_IN_NOTES, below_threshold_note
from src.index import index_name
from src.loader import list_note_files, newest_mtime, rel_source
from src.pipeline import build_index
from src.notes_io import save_note
from src.retriever import retrieve


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
    m = _hist.last_notes_message(messages)
    return [s for s in (m.get("sources") or []) if isinstance(s, dict)] if m else []


def _as_results(sources):
    """Kayıtlı kaynak sözlüklerini (parça, skor) çiftlerine çevirir (arayüz bu biçimi bekler)."""
    return [(SimpleNamespace(source=s.get("source", ""), heading=s.get("heading", ""),
                             page=s.get("page"), text=s.get("text", "")),
             float(s.get("score", 0.0) or 0.0)) for s in sources]


def last_assistant_text(messages) -> str:
    m = _hist.last_notes_message(messages)
    return (m.get("text", "") or "") if m else ""


def cited_sources(text: str, sources: list[dict]) -> list[dict]:
    """Cevapta atıf yapılan kaynaklar; atıf yoksa hepsi."""
    idxs = cited_indices(text, len(sources))
    return [sources[i - 1] for i in idxs] if idxs else list(sources)


def ask(question: str, top_k: int, backend: str, prior_messages=None,
        threshold=None, threshold_enabled=None):
    """Tüm hat: pencere -> analiz (niyet + sorgu) -> meta | kaynaklar | takip | (getir -> bütçele -> üret).
    (cevap, sonuçlar, info) döner; info = {"intent", "query"}. Hata olursa AskError fırlatır.
    threshold/threshold_enabled None ise kayıtlı ayardan okunur. En iyi skor eşiğin altındaysa LLM çağrılmaz;
    info'ya below_threshold/top_score/threshold/note eklenir."""
    history = window(prior_messages or [])
    a = analyze(question, history)
    intent, query = a["intent"], a.get("query") or question
    src = last_sources(prior_messages) if intent in ("followup", "sources") else []
    if intent in ("followup", "sources") and not src:   # dayanacak kaynak yok: normal aramaya düş
        intent = "notes"
    info = {"intent": intent, "query": query if intent == "notes" and query != question else None}
    if intent == "meta":               # asistanla ilgili soru: arama yok, kaynak yok
        try:
            return answer_meta(question), [], info
        except Exception as e:
            raise _fail_llm(e)
    if intent == "sources":            # LLM yok: önceki cevabın atıf yaptığı kaynaklar
        text = last_assistant_text(prior_messages)
        return answer_sources(text, src, question), _as_results(cited_sources(text, src)), info
    if intent == "followup":           # önceki cevabın kaynaklarıyla cevapla, yeni arama yok
        try:
            return answer_followup(question, history, src), _as_results(src), info
        except Exception as e:
            raise _fail_llm(e)
    if backend == "numpy" and index_status() is None:
        raise AskError("index", "İndeks bulunamadı.")
    try:
        load_embed_model()
        results = retrieve(query, k=top_k, backend=backend)
    except Exception as e:
        raise AskError("index" if is_index_missing(e) else "other", f"Arama başarısız: {e}")
    if threshold is None:
        threshold = settings.get_score_threshold()
    if threshold_enabled is None:
        threshold_enabled = settings.get_threshold_enabled()
    if threshold_enabled and results:
        top = float(max(s for _, s in results))
        if top < threshold:
            info.update({"intent": "notes", "query": query, "below_threshold": True, "top_score": top,
                         "threshold": threshold, "note": below_threshold_note(results, top, threshold)})
            return NOT_IN_NOTES, results, info
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
