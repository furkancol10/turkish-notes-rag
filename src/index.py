"""ADIM 4 - İNDEKSLE: Vektörleri sakla ve en benzerlerini bul. İki yöntem, aynı arayüz:
  NumpyIndex  - vektörler bir matris; arama = matris çarpımı (kosinüs benzerliği). Şeffaf, öğretici.
  ChromaIndex - ChromaDB vektör veritabanı; diske kalıcı yazar."""
import hashlib
import json
import re
import shutil
from pathlib import Path

import numpy as np

from . import config
from . import settings
from .chunker import Chunk


def folder_hash(notes_dir=None) -> str:
    p = Path(notes_dir) if notes_dir else settings.notes_dir()
    return hashlib.sha1(str(p.resolve()).encode("utf-8")).hexdigest()[:8]


def index_name(model: str, strategy: str, size: int, notes_dir=None) -> str:
    """Model/strateji/boyut + not klasörünün kısa hash'i (klasör değişince eski indeks kullanılmaz)."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", model).strip("_")[:36]
    return f"{slug}_{strategy}_{size}"[:50] + "_" + folder_hash(notes_dir)


class NumpyIndex:
    def __init__(self, name: str):
        self.dir = config.INDEX_DIR / "numpy" / name

    def build(self, chunks: list[Chunk], vecs: np.ndarray):
        # Geçici dizine yaz, başarılıysa değiştir: hata eski indeksi bozmaz
        tmp = self.dir.with_name(self.dir.name + ".tmp")
        old = self.dir.with_name(self.dir.name + ".old")
        for d in (tmp, old):
            shutil.rmtree(d, ignore_errors=True)
        tmp.mkdir(parents=True)
        try:
            np.save(tmp / "vecs.npy", vecs)
            (tmp / "chunks.json").write_text(
                json.dumps([c.__dict__ for c in chunks], ensure_ascii=False), encoding="utf-8")
            if self.dir.exists():
                self.dir.rename(old)
            tmp.rename(self.dir)
        except BaseException:
            if old.exists() and not self.dir.exists():
                old.rename(self.dir)
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        shutil.rmtree(old, ignore_errors=True)

    def _chunks(self) -> list[Chunk]:
        return [Chunk(**c) for c in json.loads((self.dir / "chunks.json").read_text("utf-8"))]

    def doc_titles(self) -> dict[str, str]:
        """source -> ilk başlık (belge filtresi için)."""
        out: dict[str, str] = {}
        for c in self._chunks():
            if not out.get(c.source):
                out[c.source] = c.heading
        return out

    def search(self, qvec: np.ndarray, k: int, sources: list[str] | None = None):
        vecs = np.load(self.dir / "vecs.npy")
        chunks = self._chunks()
        # Vektörler normalize olduğu için nokta çarpımı = kosinüs benzerliği
        scores = vecs @ qvec
        if sources:
            allowed = set(sources)
            scores = np.where([c.source in allowed for c in chunks], scores, -np.inf)
        top = [i for i in np.argsort(-scores)[:k] if np.isfinite(scores[i])]
        return [(chunks[i], float(scores[i])) for i in top]


class ChromaIndex:
    def __init__(self, name: str):
        import chromadb
        from chromadb.config import Settings
        # Telemetri kapalı: her şey yerelde kalsın
        self.client = chromadb.PersistentClient(path=str(config.INDEX_DIR / "chroma"),
                                                settings=Settings(anonymized_telemetry=False))
        self.name = name

    def build(self, chunks: list[Chunk], vecs: np.ndarray):
        tmp_name = self.name + "_tmp"
        try:
            self.client.delete_collection(tmp_name)
        except Exception:
            pass
        col = self.client.create_collection(tmp_name, metadata={"hnsw:space": "cosine"})
        try:
            col.add(ids=[c.id for c in chunks], embeddings=vecs.tolist(),
                    documents=[c.text for c in chunks],
                    metadatas=[{"source": c.source, "heading": c.heading, "page": c.page}
                               for c in chunks])
        except BaseException:
            try:
                self.client.delete_collection(tmp_name)
            except Exception:
                pass
            raise
        # Başarılı: eskisini sil, geçici koleksiyonu asıl adına çevir
        try:
            self.client.delete_collection(self.name)
        except Exception:
            pass
        col.modify(name=self.name)

    def doc_titles(self) -> dict[str, str]:
        col = self.client.get_collection(self.name)
        out: dict[str, str] = {}
        for m in col.get(include=["metadatas"])["metadatas"]:
            if not out.get(m["source"]):
                out[m["source"]] = m.get("heading", "")
        return out

    def search(self, qvec: np.ndarray, k: int, sources: list[str] | None = None):
        col = self.client.get_collection(self.name)
        where = {"source": {"$in": list(sources)}} if sources else None
        r = col.query(query_embeddings=[qvec.tolist()], n_results=min(k, col.count()) or 1, where=where)
        out = []
        for id_, doc, meta, dist in zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0]):
            out.append((Chunk(id_, meta["source"], meta["heading"], doc, meta.get("page", 0)), 1 - dist))  # mesafe -> benzerlik
        return out


def get_index(backend: str, name: str):
    return ChromaIndex(name) if backend == "chroma" else NumpyIndex(name)
