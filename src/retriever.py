"""ADIM 5 - GERİ GETİR: Soruyu embed et, indekste en benzer top-k parçayı bul.
Soru belirli bir belgeyi anıyorsa arama o belgeyle sınırlanır; kopya parçalar tekilleştirilir."""
from . import config
from .doc_filter import build_catalog, dedupe, detect_many
from .embedder import embed_query
from .index import get_index, index_name

OVERFETCH = 3
last_filter: list[str] | None = None   # son retrieve() çağrısında kullanılan belge filtresi


def retrieve_with_info(question: str, k: int = config.TOP_K, model: str = config.EMBED_MODEL,
                       backend: str = config.INDEX_BACKEND, doc_filter="auto",
                       also: list[str] | None = None):
    """-> (results [(Chunk, skor)], {"filter": [source]|None, "fallback": bool})
    doc_filter: "auto" (sorudan tespit) | None (yok) | [source, ...] (açık)."""
    global last_filter
    idx = get_index(backend, index_name(model, config.CHUNK_STRATEGY, config.CHUNK_SIZE))
    sources = None
    if isinstance(doc_filter, (list, tuple)):
        sources = list(doc_filter) or None
    elif doc_filter == "auto":
        titles = idx.doc_titles()
        sources = detect_many([question, *(also or [])], build_catalog(list(titles), titles))
    qvec = embed_query(question, model)
    n = k * OVERFETCH
    res = idx.search(qvec, n, sources) if sources else []
    fallback = False
    if sources and not res:
        sources, fallback = None, True
    if not sources:
        res = idx.search(qvec, n)
    last_filter = sources
    return dedupe(res, k), {"filter": sources, "fallback": fallback}


def retrieve(question: str, k: int = config.TOP_K, model: str = config.EMBED_MODEL,
             backend: str = config.INDEX_BACKEND, doc_filter="auto"):
    return retrieve_with_info(question, k, model, backend, doc_filter)[0]  # [(Chunk, skor)]
