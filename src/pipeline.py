"""Yükle -> parçala -> embed -> indeksle akışı; CLI, Streamlit ve masaüstü ortak kullanır."""
from dataclasses import dataclass

from . import config, settings
from .chunker import chunk_docs
from .embedder import embed_passages
from .formats import NO_NOTES_MSG
from .index import get_index, index_name
from .loader import load_report


@dataclass
class IndexResult:
    n_docs: int
    n_chunks: int
    n_skipped: int

    def summary(self) -> str:
        return (f"{self.n_docs} dosya → {self.n_chunks} parça; "
                f"atlanan: {self.n_skipped} (desteklenmeyen/okunamayan)")


def build_index() -> IndexResult:
    rep = load_report()
    if not rep.docs:
        raise ValueError(f"{NO_NOTES_MSG} Klasör: {settings.notes_dir()}")
    chunks = chunk_docs(rep.docs)
    vecs = embed_passages([c.text for c in chunks])
    name = index_name(config.EMBED_MODEL, config.CHUNK_STRATEGY, config.CHUNK_SIZE)
    for backend in ("numpy", "chroma"):
        get_index(backend, name).build(chunks, vecs)
    return IndexResult(len(rep.docs), len(chunks), rep.n_skipped)
