"""ADIM 3 - EMBED: Metni sayı vektörüne çevir. Anlamca yakın metinler yakın vektör olur."""
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from . import config


@lru_cache(maxsize=None)
def _model(name: str) -> SentenceTransformer:
    return SentenceTransformer(name, device="cpu")  # LLM GPU'da, embedding CPU'da


def _encode(texts: list[str], prefix: str, model: str) -> np.ndarray:
    vecs = _model(model).encode([prefix + t for t in texts], batch_size=8,
                                normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype=np.float32)


def embed_passages(texts: list[str], model: str = config.EMBED_MODEL) -> np.ndarray:
    return _encode(texts, config.PASSAGE_PREFIX.get(model, ""), model)


def embed_query(text: str, model: str = config.EMBED_MODEL) -> np.ndarray:
    return _encode([text], config.QUERY_PREFIX.get(model, ""), model)[0]
