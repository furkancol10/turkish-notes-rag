"""Chroma ve numpy aynı kosinüs skorunu (yüksek = iyi) döndürmeli."""
import numpy as np

from src import config
from src.chunker import Chunk
from src.index import ChromaIndex, NumpyIndex


def test_top1_score_parity(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "INDEX_DIR", tmp_path)
    rng = np.random.default_rng(0)
    vecs = rng.normal(size=(6, 32)).astype("float32")
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    chunks = [Chunk(f"n{i}.md#0", f"n{i}.md", "H", f"metin {i}", 0) for i in range(6)]
    q = vecs[2] * 0.8 + vecs[4] * 0.2
    q = (q / np.linalg.norm(q)).astype("float32")
    n, c = NumpyIndex("tiny_idx"), ChromaIndex("tiny_idx")
    n.build(chunks, vecs)
    c.build(chunks, vecs)
    (nc, ns), (cc, cs) = n.search(q, 3)[0], c.search(q, 3)[0]
    assert nc.id == cc.id == "n2.md#0"
    assert abs(ns - cs) < 0.01 and ns > 0.9
