"""ADIM 4 - İNDEKSLE: Vektörleri sakla ve en benzerlerini bul. İki yöntem, aynı arayüz:
  NumpyIndex  - vektörler bir matris; arama = matris çarpımı (kosinüs benzerliği). Şeffaf, öğretici.
  ChromaIndex - ChromaDB vektör veritabanı; diske kalıcı yazar."""
import json
import re

import numpy as np

from . import config
from .chunker import Chunk


def index_name(model: str, strategy: str, size: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", model).strip("_")[:40]
    return f"{slug}_{strategy}_{size}"[:60]


class NumpyIndex:
    def __init__(self, name: str):
        self.dir = config.INDEX_DIR / "numpy" / name

    def build(self, chunks: list[Chunk], vecs: np.ndarray):
        self.dir.mkdir(parents=True, exist_ok=True)
        np.save(self.dir / "vecs.npy", vecs)
        (self.dir / "chunks.json").write_text(
            json.dumps([c.__dict__ for c in chunks], ensure_ascii=False), encoding="utf-8")

    def search(self, qvec: np.ndarray, k: int):
        vecs = np.load(self.dir / "vecs.npy")
        chunks = [Chunk(**c) for c in json.loads((self.dir / "chunks.json").read_text("utf-8"))]
        # Vektörler normalize olduğu için nokta çarpımı = kosinüs benzerliği
        scores = vecs @ qvec
        top = np.argsort(-scores)[:k]
        return [(chunks[i], float(scores[i])) for i in top]


class ChromaIndex:
    def __init__(self, name: str):
        import chromadb
        self.client = chromadb.PersistentClient(path=str(config.INDEX_DIR / "chroma"))
        self.name = name

    def build(self, chunks: list[Chunk], vecs: np.ndarray):
        try:
            self.client.delete_collection(self.name)
        except Exception:
            pass
        col = self.client.create_collection(self.name, metadata={"hnsw:space": "cosine"})
        col.add(ids=[c.id for c in chunks], embeddings=vecs.tolist(),
                documents=[c.text for c in chunks],
                metadatas=[{"source": c.source, "heading": c.heading} for c in chunks])

    def search(self, qvec: np.ndarray, k: int):
        col = self.client.get_collection(self.name)
        r = col.query(query_embeddings=[qvec.tolist()], n_results=k)
        out = []
        for id_, doc, meta, dist in zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0]):
            out.append((Chunk(id_, meta["source"], meta["heading"], doc), 1 - dist))  # mesafe -> benzerlik
        return out


def get_index(backend: str, name: str):
    return ChromaIndex(name) if backend == "chroma" else NumpyIndex(name)
