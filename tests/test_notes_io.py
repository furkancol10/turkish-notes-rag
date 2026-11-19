import pytest

from src import settings
from src.notes_io import save_note


@pytest.fixture(autouse=True)
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    d = tmp_path / "notes"
    settings.set_override(str(d))
    yield d
    settings.set_override(None)


def test_same_name_not_overwritten(cfg):
    assert save_note("a.md", b"bir") == "a.md"
    assert save_note("a.md", b"iki") == "a (2).md"
    assert save_note("a.md", b"uc") == "a (3).md"
    assert (cfg / "a.md").read_bytes() == b"bir"
    assert (cfg / "a (2).md").read_bytes() == b"iki"
