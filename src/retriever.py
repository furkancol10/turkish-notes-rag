"""ADIM 5 - GERİ GETİR: Soruyu embed et, indekste en benzer top-k parçayı bul."""
from . import config
from .embedder import embed_query
from .index import get_index, index_name


def retrieve(question: str, k: int = config.TOP_K, model: str = config.EMBED_MODEL,
             backend: str = config.INDEX_BACKEND):
    name = index_name(model, config.CHUNK_STRATEGY, config.CHUNK_SIZE)
    return get_index(backend, name).search(embed_query(question, model), k)  # [(Chunk, skor)]
