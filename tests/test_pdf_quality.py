import random
import time

import pymupdf
from docx import Document

from src import settings
from src.examples import example_questions
from src.formats import parse
from src.loader import load_report
from src.notes_io import save_note


def _pdf(path, pages, sizes=None):
    d = pymupdf.open()
    for i, lines in enumerate(pages):
        p = d.new_page()
        y = 60
        for j, l in enumerate(lines):
            p.insert_text((50, y), l, fontsize=(sizes or {}).get(j, 10))
            y += 22
    d.save(str(path))


def test_repeated_header_footer_stripped_and_pages_kept(tmp_path):
    pages = [["RAG Proje Raporu", f"Sayfa {i}", f"Icerik benzersiz{i} burada", "Ikinci satir", f"{i}"]
             for i in range(1, 6)]
    _pdf(tmp_path / "a.pdf", pages)
    r = parse(tmp_path / "a.pdf")
    assert "Raporu" not in r.text and "Sayfa" not in r.text
    assert [n for n, _ in r.pages] == [1, 2, 3, 4, 5]
    assert "benzersiz3" in r.pages[2][1]


def test_pdf_headings_skip_generic_and_pick_real(tmp_path):
    pages = [["1. Gercek Bolum Basligi", "govde metni burada", "govde metni iki"],
             ["Raporu", "govde"], ["govde"]]
    _pdf(tmp_path / "a.pdf", pages, sizes={0: 18})
    qs = example_questions(tmp_path, rng=random.Random(1))
    assert qs and all("«Raporu»" not in q for q in qs)
    assert "Gercek Bolum Basligi" in qs[0]


def test_encrypted_pdf_skipped(tmp_path):
    d = pymupdf.open()
    d.new_page().insert_text((50, 50), "gizli metin " * 10)
    d.save(str(tmp_path / "e.pdf"), encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="x", owner_pw="y")
    rep = load_report(tmp_path)
    assert not rep.docs and len(rep.skipped) == 1


def test_corrupt_files_skipped_no_crash(tmp_path):
    (tmp_path / "b.docx").write_bytes(b"not a zip")
    (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4 garbage")
    rep = load_report(tmp_path)
    assert not rep.docs and len(rep.skipped) == 2


def test_html_huge_script_removed_fast(tmp_path):
    (tmp_path / "h.html").write_text(
        "<html><head><style>.a{color:red}</style></head><body><h1>Baslik</h1><p>Metin</p>"
        "<script>" + "var x=1;" * 500000 + "</script></body></html>", encoding="utf-8")
    t = time.time()
    r = parse(tmp_path / "h.html")
    assert time.time() - t < 10
    assert "var x" not in r.text and "color:red" not in r.text and "Metin" in r.text


def test_upload_binary_identical(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    dst = tmp_path / "notes"
    dst.mkdir()
    settings.set_notes_dir(dst)
    p = tmp_path / "src.docx"
    Document().save(str(p))
    data = p.read_bytes()
    assert save_note("../x/yeni.docx", data) == "yeni.docx"
    assert (dst / "yeni.docx").read_bytes() == data
