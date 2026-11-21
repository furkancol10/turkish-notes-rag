import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from desktop.settings_dialog import SettingsDialog

INFO = {"embed_model": "bge-m3", "llm_model": "qwen", "chunk_size": 800, "num_ctx": 4096,
        "notes_dir": "/tmp/notlar"}

TH = {"score_threshold": 0.40, "threshold_enabled": True, "show_citations": True}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def make(app, top_k=7, backend="numpy", info=INFO):
    return SettingsDialog(None, top_k=top_k, backend=backend, info=info)


def step(d, sym):
    return next(b for b in d.findChildren(QPushButton) if b.text() == sym)


def test_initial(app):
    assert make(app).values() == {"top_k": 7, "backend": "numpy", **TH}
    assert make(app, 3, "chroma").values() == {"top_k": 3, "backend": "chroma", **TH}


def test_missing_info(app):
    assert make(app, info={}).values()["top_k"] == 7


def test_stepper_bounds(app):
    d = make(app, 15)
    step(d, "+").click()
    assert d.values()["top_k"] == 15
    d = make(app, 1)
    step(d, "−").click()
    assert d.values()["top_k"] == 1
    step(d, "+").click()
    assert d.values()["top_k"] == 2


def test_backend_toggle_and_reset(app):
    d = make(app, 4, "chroma")
    d.btn_numpy.click()
    step(d, "+").click()
    assert d.values() == {"top_k": 5, "backend": "numpy", **TH}
    d.btn_reset.click()
    assert d.values() == {"top_k": 10, "backend": "chroma", **TH}
    assert d.btn_chroma.isChecked() and not d.btn_numpy.isChecked()


def test_cancel_and_save(app):
    d = make(app)
    step(d, "+").click()
    d.btn_cancel.click()
    assert d.result() == SettingsDialog.Rejected
    d2 = make(app)
    d2.btn_save.click()
    assert d2.result() == SettingsDialog.Accepted


def test_threshold_values_reset_and_disable(app):
    d = SettingsDialog(None, top_k=7, backend="numpy", info=INFO, score_threshold=0.6,
                       threshold_enabled=False)
    v = d.values()
    assert v["score_threshold"] == 0.6 and v["threshold_enabled"] is False
    assert not d.th.isEnabled()
    d.th_enabled.setChecked(True)
    d.th.setValue(0.33)
    assert d.values()["score_threshold"] == 0.33 and d.th.isEnabled()
    d.th.setValue(5)
    assert d.values()["score_threshold"] == 0.9
    d.btn_reset.click()
    assert (d.values()["score_threshold"], d.values()["threshold_enabled"]) == (0.40, True)


def test_show_citations_toggle_and_reset(app):
    d = SettingsDialog(None, top_k=7, backend="numpy", info=INFO, show_citations=False)
    assert d.show_citations.text() == "Atıf numaralarını göster"
    assert d.values()["show_citations"] is False
    d.show_citations.setChecked(True)
    assert d.values()["show_citations"] is True
    d.show_citations.setChecked(False)
    d.btn_reset.click()
    assert d.values()["show_citations"] is True
