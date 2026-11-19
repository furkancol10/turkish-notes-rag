import numpy as np
import pytest

from src import config, retriever
from src.chunker import Chunk
from src.index import get_index


def mk(tmp_path, monkeypatch, backend):
    monkeypatch.setattr(config, "INDEX_DIR", tmp_path)
    chunks = [Chunk("a#0", "gptRag.pdf", "GPT", "gpt önerileri alfa", 1),
              Chunk("b#0", "notlar.md", "Not", "başka konu beta", 0),
              Chunk("c#0", "diger.md", "Diger", "bambaşka gamma", 0)]
    vecs = np.array([[0.1, 1, 0], [1, 0.1, 0], [0.9, 0.3, 0]], dtype=np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    get_index(backend, "tst").build(chunks, vecs)
    monkeypatch.setattr(retriever, "index_name", lambda *a, **k: "tst")
    monkeypatch.setattr(retriever, "embed_query", lambda q, m: np.array([1, 0, 0], dtype=np.float32))


@pytest.mark.parametrize("backend", ["numpy", "chroma"])
def test_low_score_filtered_merges_unfiltered(tmp_path, monkeypatch, backend):
    mk(tmp_path, monkeypatch, backend)
    res, info = retriever.retrieve_with_info("chatgpt ne demiş", 3, backend=backend)
    assert info["fallback"] == "low_score" and info["filter"] == ["gptRag.pdf"]
    ids = [c.id for c, _ in res]
    assert len(ids) == len(set(ids)) == 3
    assert ids[0] == "b#0"           # yüksek skorlu filtresiz sonuç öne geçti
    assert "a#0" in ids


@pytest.mark.parametrize("backend", ["numpy", "chroma"])
def test_empty_filtered_reports_empty(tmp_path, monkeypatch, backend):
    mk(tmp_path, monkeypatch, backend)
    res, info = retriever.retrieve_with_info("x", 3, backend=backend, doc_filter=["yok.md"])
    assert info["fallback"] == "empty" and info["filter"] is None and len(res) == 3


@pytest.mark.parametrize("backend", ["numpy", "chroma"])
def test_no_fallback_when_score_high(tmp_path, monkeypatch, backend):
    mk(tmp_path, monkeypatch, backend)
    res, info = retriever.retrieve_with_info("x", 3, backend=backend, doc_filter=["notlar.md"])
    assert info["fallback"] is None and [c.id for c, _ in res] == ["b#0"]
