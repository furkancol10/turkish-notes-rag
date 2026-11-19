from types import SimpleNamespace

from src import generator
from src.sources import answer_sources, cited_indices


def test_cited_formats():
    assert cited_indices("x [2], [5] y [2]", 5) == [2, 5]
    assert cited_indices("[1], [3]", 3) == [1, 3]
    assert cited_indices("[1, 3]", 3) == [1, 3]
    assert cited_indices("[2-4]", 5) == [2, 3, 4]
    assert cited_indices("[9] [0] [2]", 3) == [2]
    assert cited_indices("atıf yok", 3) == []


SRC = [
    {"source": "a.pdf", "heading": "Giriş", "page": 3, "text": ""},
    {"source": "b.md", "heading": "", "page": None, "text": ""},
    {"source": "a.pdf", "heading": "Giriş", "page": 5, "text": ""},
    {"source": "a.pdf", "heading": "Giriş", "page": 3, "text": ""},
]


def test_grouping_pages_dedupe():
    out = answer_sources("Evet [1], [3], [4]", SRC)
    assert out.count("**a.pdf**") == 1 and "b.md" not in out
    assert "s. 3, 5" in out and "Giriş" in out


def test_only_cited():
    out = answer_sources("Evet [2]", SRC)
    assert "b.md" in out and "a.pdf" not in out


def test_no_cite_lists_all():
    out = answer_sources("atıfsız", SRC)
    assert "Cevapta açık atıf yoktu; getirilen kaynaklar:" in out
    assert "a.pdf" in out and "b.md" in out


def test_page_question():
    assert "sayfa 3, 5" in answer_sources("[1] [3]", SRC, "hangi sayfada?")


def test_no_sources():
    assert answer_sources("x", []) == "Önceki cevap notlardan bir kaynağa dayanmıyordu."


def test_prompt_header_has_page_and_system_allows_files():
    c = SimpleNamespace(source="dosya.pdf", heading="Bölüm", page=3, text="t")
    p = generator.build_prompt("q", [(c, 1.0)])
    assert "[1] (dosya.pdf, s. 3 / Bölüm)" in p
    assert "hangi dosyada" in generator.SYSTEM
