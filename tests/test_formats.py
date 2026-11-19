import pymupdf
import pytest
from docx import Document

from src import config
from src.chunker import chunk_docs, chunk_label
from src.formats import SUFFIXES, UPLOAD_TYPES
from src.loader import load_notes, load_report
from src.notes_io import safe_note_name


def make_pdf(path, pages):
    d = pymupdf.open()
    for t in pages:
        p = d.new_page()
        if t:
            p.insert_text((72, 72), t)
    d.save(str(path))


def make_docx(path):
    d = Document()
    d.add_heading("Giris", 1)
    d.add_paragraph("Metin paragrafi burada.")
    d.add_heading("Veri", 2)
    t = d.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text = "HucreA"
    t.rows[0].cells[1].text = "HucreB"
    d.save(str(path))


def test_registry_shared():
    for s in (".pdf", ".docx", ".html", ".md", ".txt"):
        assert s in SUFFIXES
    assert "pdf" in UPLOAD_TYPES
    assert safe_note_name("a.pdf") == "a.pdf" and safe_note_name("a.exe") is None


def test_pdf_pages_and_chunks(tmp_path):
    make_pdf(tmp_path / "a.pdf", ["Birinci sayfa " * 10, "Ikinci sayfa " * 10])
    docs = load_notes(tmp_path)
    assert [p for p, _ in docs[0].pages] == [1, 2]
    chunks = chunk_docs(docs, "fixed", 80, 10)
    assert {c.page for c in chunks} == {1, 2}
    assert all(("Birinci" in c.text) == (c.page == 1) for c in chunks)
    assert chunk_label(chunks[0]) == "a.pdf, s. 1"


def test_scanned_pdf_skipped(tmp_path):
    make_pdf(tmp_path / "scan.pdf", [None, None])
    rep = load_report(tmp_path)
    assert rep.docs == [] and "OCR" in rep.skipped[0][1]


def test_corrupt_files_skipped_not_crash(tmp_path):
    (tmp_path / "bad.pdf").write_bytes(b"not a pdf")
    (tmp_path / "bad.docx").write_bytes(b"not a docx")
    (tmp_path / "ok.md").write_text("# T\nhi", "utf-8")
    (tmp_path / "x.png").write_bytes(b"x")
    with pytest.warns(UserWarning):
        rep = load_report(tmp_path)
    assert [d.source for d in rep.docs] == ["ok.md"]
    assert len(rep.skipped) == 2 and rep.unsupported == 1 and rep.n_skipped == 3


def test_docx_headings_and_table(tmp_path):
    make_docx(tmp_path / "d.docx")
    d = load_notes(tmp_path)[0]
    assert "# Giris" in d.text and "## Veri" in d.text and "HucreA | HucreB" in d.text
    chunks = chunk_docs([d], "heading")
    assert {c.heading for c in chunks} == {"Giris", "Veri"}
    assert any("HucreB" in c.text for c in chunks if c.heading == "Veri")


def test_html_clean(tmp_path):
    (tmp_path / "p.html").write_text(
        "<html><head><title>T</title><style>.a{}</style></head><body><nav>MENU</nav>"
        "<script>var x='SCRIPTSEN'</script><h1>Ana</h1><p>Bir</p><p>Iki</p>"
        "<h2>Alt</h2><p>Uc</p><footer>FOOT</footer></body></html>", "utf-8")
    d = load_notes(tmp_path)[0]
    for bad in ("MENU", "SCRIPTSEN", "FOOT", "a{}"):
        assert bad not in d.text
    assert "# Ana" in d.text and "## Alt" in d.text and "Bir\n\nIki" in d.text
    assert {c.heading for c in chunk_docs([d], "heading")} == {"Ana", "Alt"}


def test_md_txt_unchanged(tmp_path):
    (tmp_path / "a.md").write_text("# A\nx", "utf-8")
    (tmp_path / "b.txt").write_text("plain", "utf-8")
    d = load_notes(tmp_path)
    assert [x.text for x in d] == ["# A\nx", "plain"] and all(x.pages is None for x in d)
    assert all(c.page == 0 for c in chunk_docs(d, "fixed", config.CHUNK_SIZE, 0))


def test_example_questions(tmp_path):
    import random
    from src.examples import example_questions
    (tmp_path / "a.md").write_text("# Fotosentez (ÖRNEK NOT)\nx\n## 12\n", "utf-8")
    (tmp_path / "b.md").write_text("# " + "uzun başlık " * 10 + "\n", "utf-8")
    make_docx(tmp_path / "c.docx")
    make_pdf(tmp_path / "d.pdf", ["Rapor Başlığı\nmetin"])
    (tmp_path / "e.html").write_text("<h1>Web Sayfası</h1><p>x</p>", "utf-8")
    qs = example_questions(tmp_path, rng=random.Random(1))
    assert len(qs) == 3 and len(set(qs)) == 3
    assert all(q.startswith("«") and "ÖRNEK" not in q for q in qs)
    assert all(len(q) < 90 for q in qs)
    assert example_questions(tmp_path / "yok") == []
