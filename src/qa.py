"""Tek soru-cevap hattı (masaüstü, CLI ve Streamlit ortak):
pencere -> analiz (niyet + sorgu) -> meta | kaynaklar | takip | (getir -> eşik -> varlık koruması -> bütçele -> üret)."""
from datetime import datetime
from types import SimpleNamespace

from . import config, entities, history as _hist, settings
from .conversation import fit_budget, window
from .embedder import warmup_query_model
from .formats import NOT_IN_NOTES, below_threshold_note
from .generator import answer, answer_followup, answer_meta
from .index import index_name
from .retriever import retrieve
from .rewriter import analyze
from .sources import answer_sources, cited_indices


def load_embed_model():
    """Modeli bir kez yükler (lru_cache), sonraki çağrılar anında döner."""
    return warmup_query_model()


def index_status():
    """Son indeksleme zamanı (numpy indeksinin dosya tarihi) veya None."""
    f = config.INDEX_DIR / "numpy" / index_name(
        config.EMBED_MODEL, config.CHUNK_STRATEGY, config.CHUNK_SIZE) / "vecs.npy"
    return datetime.fromtimestamp(f.stat().st_mtime) if f.exists() else None


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


def _doc_catalog(backend):
    """Belge adı/başlık takma adları (doc_filter'ın ele aldığı varlıkları ayıklamak için); alınamazsa None."""
    try:
        from .doc_filter import build_catalog
        from .index import get_index
        idx = get_index(backend, index_name(config.EMBED_MODEL, config.CHUNK_STRATEGY, config.CHUNK_SIZE))
        titles = idx.doc_titles()
        return build_catalog(list(titles), titles)
    except Exception:
        return None


def ask(question: str, *, top_k: int, backend: str, prior_messages=None,
        threshold=None, threshold_enabled=None, entity_guard=None):
    """(cevap, sonuçlar, info) döner; info = {"intent", "query"}. Hata olursa AskError fırlatır.
    threshold/threshold_enabled None ise kayıtlı ayardan, entity_guard None ise config'ten okunur.
    En iyi skor eşiğin altındaysa LLM çağrılmaz; info'ya below_threshold/top_score/threshold/note eklenir."""
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
    if entity_guard is None:
        entity_guard = config.ENTITY_GUARD_ENABLED
    if threshold_enabled and results:
        top = float(max(s for _, s in results))
        if top < threshold:
            info.update({"intent": "notes", "query": query, "below_threshold": True, "top_score": top,
                         "threshold": threshold, "note": below_threshold_note(results, top, threshold)})
            return NOT_IN_NOTES, results, info
    if entity_guard and results:
        miss = entities.missing(query, [c.text for c, _ in results], _doc_catalog(backend))
        if miss:
            info.update({"intent": "notes", "entity_missing": miss,
                         "note": "Notlarda " + ", ".join(f"“{m}”" for m in miss) + " geçen bir bölüm bulunamadı."})
            return NOT_IN_NOTES, results, info
    history, results = fit_budget(history, results, question)
    try:
        return answer(question, results, history), results, info
    except Exception as e:
        raise _fail_llm(e)


def assistant_message(question: str, ans: str, results, info: dict) -> dict:
    """Sohbet geçmişine (history.py biçimi) eklenecek asistan mesajı."""
    msg = {"role": "assistant", "text": ans, "sources": _hist.sources_from_results(results),
           "intent": info.get("intent", "notes")}
    for k in ("below_threshold", "top_score", "threshold", "note", "entity_missing"):
        if k in info:
            msg[k] = info[k]
    if info.get("query") and info["query"] != question:
        msg["query"] = info["query"]
    return msg
