import random

from src.examples import example_questions, _title_of


def _notes(tmp_path):
    (tmp_path / "a.md").write_text(
        "# Hibrit Arama Rehberi\n\n## Adım 5: Raporlama\n\n## Temizleme\n\n"
        + "hibrit arama ve reranking birlikte kullanılır. " * 5
        + "\n\nRAG'in tek bir temel sorusuna farklı yaklaşımlar vardır.\n", encoding="utf-8")
    (tmp_path / "b.md").write_text(
        "# Veri Yapıları Notları\n\n" + "ikili ağaç düğümleri dolaşılır. " * 5, encoding="utf-8")
    (tmp_path / "c.md").write_text("# Sebze Yemekleri Tarifi\n\n" + "zeytinyağı kullanılır, patlıcan kızartılır. " * 5,
                                   encoding="utf-8")


def test_title_filter():
    assert _title_of("Adım 5: Raporlama") is None          # tek kelime
    assert _title_of("8 uygulamalı proje önerisi") is None  # alt başlık
    assert _title_of("Retrieval-Augmented Generation öğrenimi için") is None
    assert _title_of("Temizleme") is None
    assert _title_of("RAG'in tek bir temel sorusuna farklı yaklaşımlar vardır.") is None
    assert _title_of("1. Hibrit Arama Rehberi") == "Hibrit Arama Rehberi"
    assert _title_of("Adım 3: Re-ranking Ekleme") == "Re-ranking Ekleme"


def test_examples_quality_and_variety(tmp_path):
    _notes(tmp_path)
    seen = set()
    for seed in range(10):
        qs = example_questions(tmp_path, rng=random.Random(seed))
        assert 1 <= len(qs) <= 3 and len(set(qs)) == len(qs)
        for q in qs:
            assert len(q) <= 50 and "…" not in q and "«" not in q
            assert "Raporlama" not in q and "Temizleme" not in q and "RAG'in tek" not in q
            seen.add(q)
    assert any("hibrit arama" in q or "reranking" in q for q in seen)   # TF-IDF kavramı
    assert len(seen) > 4                                               # döner


def test_button_never_clips(tmp_path, monkeypatch):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from desktop.chat_view import EmptyState
    e = EmptyState()
    e.resize(220, 400)
    e.set_examples(["Çok uzun bir başlık adı burada geçiyor gerçekten neyi anlatıyor?"])
    e.show()
    QApplication.processEvents()
    b = e._btns[0]
    assert b.width() <= e.width()
    assert b.fontMetrics().horizontalAdvance(b.text()) <= b.width()
    e.close(); e.deleteLater()
    assert b.toolTip().startswith("Çok uzun")
