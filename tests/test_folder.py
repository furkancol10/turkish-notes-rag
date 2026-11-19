import json

import pytest

from src import index, settings
from src.loader import load_notes


@pytest.fixture(autouse=True)
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    settings.set_override(None)
    yield
    settings.set_override(None)


def test_settings_roundtrip_and_default(tmp_path):
    assert settings.notes_dir() == settings.DEFAULT_NOTES_DIR
    d = tmp_path / "n"
    d.mkdir()
    settings.set_notes_dir(d)
    assert settings.notes_dir() == d.resolve()
    settings.reset_notes_dir()
    assert settings.notes_dir() == settings.DEFAULT_NOTES_DIR


def test_settings_corrupt_and_missing_dir(tmp_path):
    p = settings.settings_path()
    p.parent.mkdir(parents=True)
    p.write_text("{bozuk", encoding="utf-8")
    assert settings.get("notes_dir") is None
    assert settings.notes_dir() == settings.DEFAULT_NOTES_DIR
    p.write_text(json.dumps({"notes_dir": str(tmp_path / "yok")}))
    assert settings.notes_dir() == settings.DEFAULT_NOTES_DIR
    settings.set("x", 1)   # bozuk/eksik dosya üzerine yazabilir
    assert settings.get("x") == 1
    with pytest.raises(ValueError):
        settings.set_notes_dir(tmp_path / "yok")


def test_recursive_loader(tmp_path):
    for rel in ["a.md", "x/a.md", "x/y/b.txt", ".gizli/c.md", ".git/d.md",
                "node_modules/e.md", ".venv/f.md", "x/g.pdf"]:
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(rel)
    (tmp_path / "x" / "loop").symlink_to(tmp_path, target_is_directory=True)
    docs = load_notes(tmp_path)
    assert [d.source for d in docs] == ["a.md", "x/a.md", "x/y/b.txt"]
    assert {d.text for d in docs} == {"a.md", "x/a.md", "x/y/b.txt"}


def test_index_name_differs_per_folder(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    na, nb = (index.index_name("BAAI/bge-m3", "fixed", 512, d) for d in (a, b))
    assert na != nb and len(na) <= 60
    assert na == index.index_name("BAAI/bge-m3", "fixed", 512, a)
    settings.set_override(a)
    assert index.index_name("BAAI/bge-m3", "fixed", 512) == na


def test_non_utf8_and_broken_symlink_skipped(tmp_path):
    (tmp_path / "ok.md").write_text("merhaba", encoding="utf-8")
    (tmp_path / "bad.txt").write_bytes(b"\xff\xfe\x00bad\x80")
    (tmp_path / "kirik.md").symlink_to(tmp_path / "yok.md")
    with pytest.warns(UserWarning):
        docs = load_notes(tmp_path)
    assert [d.source for d in docs] == ["ok.md"]
