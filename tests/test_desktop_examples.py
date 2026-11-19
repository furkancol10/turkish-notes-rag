import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_examples_refresh_on_folder_change(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from desktop import main as m
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    (a / "x.md").write_text("# Alfa Konusu\nmetin", encoding="utf-8")
    (b / "y.md").write_text("# Beta Konusu\nmetin", encoding="utf-8")
    from src import settings
    settings.set_notes_dir(a)
    w = m.MainWindow()
    texts = lambda: [x.text() for x in w.chat._empty._btns]
    assert any("Alfa" in t for t in texts())
    settings.set_notes_dir(b)
    w.refresh_side()
    assert any("Beta" in t for t in texts()) and not any("Alfa" in t for t in texts())
