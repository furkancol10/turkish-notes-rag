import numpy as np
import pytest

from src import config, retriever
from src.chunker import Chunk
from src.doc_filter import build_catalog, dedupe, detect
from src.index import get_index

SRC = ["gptRag.pdf", "geminiRapor.pdf", "deepseek_notlar.md", "toplanti_proje_nova.md",
       "toplanti_proje_atlas.md", "toplanti_haftalik.md", "ders_rag_giris.md"]
CAT = build_catalog(SRC, {"toplanti_proje_nova.md": "Proje Nova Toplantısı"})


def test_aliases():
    assert ("gpt",) in CAT["gptRag.pdf"]
    assert ("rag",) not in CAT["gptRag.pdf"]
    assert ("nova",) in CAT["toplanti_proje_nova.md"]
    assert ("proje", "nova") in CAT["toplanti_proje_nova.md"]
    assert ("proje",) not in CAT["toplanti_proje_nova.md"]


@pytest.mark.parametrize("q,exp", [
    ("chatgpt hangi projeleri önermiş", ["gptRag.pdf"]),
    ("OpenAI ne demiş", ["gptRag.pdf"]),
    ("gemini raporu ne diyor", ["geminiRapor.pdf"]),
    ("Proje Nova bütçesi nedir?", ["toplanti_proje_nova.md"]),
    ("Nova'nın bütçesi", ["toplanti_proje_nova.md"]),
    ("chatgpt ile deepseek farkı", ["deepseek_notlar.md", "gptRag.pdf"]),
    ("rag nedir", None), ("proje notları rapor", None), ("toplantı ne zaman", None),
])
def test_detect(q, exp):
    assert detect(q, CAT) == exp


def test_too_many_docs_none():
    q = "chatgpt gemini deepseek nova"
    assert detect(q, CAT) is None


def mk(tmp_path, monkeypatch, backend):
    monkeypatch.setattr(config, "INDEX_DIR", tmp_path)
    chunks = [Chunk("a#0", "gptRag.pdf", "GPT", "gpt önerileri alfa", 1),
              Chunk("b#0", "geminiRapor.pdf", "Gemini", "gemini önerileri alfa", 1),
              Chunk("c#0", "notlar.md", "Not", "başka konu beta", 0)]
    vecs = np.array([[1, 0, 0], [0.99, 0.14, 0], [0, 0, 1]], dtype=np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    get_index(backend, "tst").build(chunks, vecs)
    monkeypatch.setattr(retriever, "index_name", lambda *a, **k: "tst")
    monkeypatch.setattr(retriever, "embed_query", lambda q, m: np.array([1, 0, 0], dtype=np.float32))


@pytest.mark.parametrize("backend", ["numpy", "chroma"])
def test_filtered_retrieval(tmp_path, monkeypatch, backend):
    mk(tmp_path, monkeypatch, backend)
    res, info = retriever.retrieve_with_info("gemini ne önermiş", 3, backend=backend)
    assert [c.source for c, _ in res] == ["geminiRapor.pdf"] and info["filter"] == ["geminiRapor.pdf"]
    assert retriever.last_filter == ["geminiRapor.pdf"]
    off = retriever.retrieve("gemini ne önermiş", 3, backend=backend, doc_filter=None)
    assert len(off) == 3
    res, info = retriever.retrieve_with_info("ne var", 3, backend=backend)
    assert info["filter"] is None and len(res) == 3
    assert len(retriever.retrieve("x", 3, backend=backend, doc_filter=["notlar.md"])) == 1


@pytest.mark.parametrize("backend", ["numpy", "chroma"])
def test_fallback_when_empty(tmp_path, monkeypatch, backend):
    mk(tmp_path, monkeypatch, backend)
    res, info = retriever.retrieve_with_info("x", 3, backend=backend, doc_filter=["yok.md"])
    assert info["fallback"] and info["filter"] is None and len(res) == 3


def test_dedupe_prefers_pdf_and_fills_k():
    t = "Aynı metin burada geçiyor ve uzun uzun devam ediyor"
    r = [(Chunk("1", "x.html", "", t), .9), (Chunk("2", "x.pdf", "", t, 4), .9),
         (Chunk("3", "y.md", "", "tamamen farklı"), .5), (Chunk("4", "z.md", "", "bir başka"), .4)]
    out = dedupe(r, 3)
    assert [c.source for c, _ in out] == ["x.pdf", "y.md", "z.md"]
    near = [(Chunk("1", "a", "", " ".join(f"w{i}" for i in range(30))), 1),
            (Chunk("2", "b", "", " ".join(f"w{i}" for i in range(29)) + " zz"), 1)]
    assert len(dedupe(near)) == 1


NOTES = ["kisisel_butce.md", "toplanti_proje_nova.md", "toplanti_proje_atlas.md", "tarif_imam_bayildi.md",
         "tarif_karniyarik.md", "tarif_menemen.md", "gptRag.pdf", "geminiRapor.pdf", "seyahat_istanbul.md",
         "seyahat_eskisehir.md", "kitap_sapiens.md"]
NCAT = build_catalog(NOTES, {"toplanti_proje_nova.md": "Proje Nova Toplantısı"})


@pytest.mark.parametrize("q,exp", [
    ("Proje Nova bütçesi nedir?", ["toplanti_proje_nova.md"]),
    ("kişisel bütçemde kira ne kadar", ["kisisel_butce.md"]),
    ("imam bayıldı tarifi", ["tarif_imam_bayildi.md"]),
    ("karnıyarık tarifi nasıl", ["tarif_karniyarik.md"]),
    ("chatgpt hangi projeleri önermiş", ["gptRag.pdf"]),
    ("gemini ve chatgpt'yi karşılaştır", ["geminiRapor.pdf", "gptRag.pdf"]),
    ("seyahat planı nedir", None),
    ("genel olarak ne yapmalıyım", None),
])
def test_detect_specificity(q, exp):
    assert detect(q, NCAT) == exp
