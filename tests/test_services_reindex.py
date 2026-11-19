import numpy as np
import pytest

from src import config, pipeline, settings
from desktop import services


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setattr(config, "INDEX_DIR", tmp_path / "idx")
    notes = tmp_path / "notes"
    notes.mkdir()
    settings.set_override(str(notes))
    monkeypatch.setattr(pipeline, "embed_passages",
                        lambda t: np.ones((len(t), 4), dtype="float32") / 2)
    monkeypatch.setattr(pipeline, "release_index_model", lambda: None)
    monkeypatch.setattr(pipeline, "unload_llm", lambda: None)
    monkeypatch.setattr(pipeline, "resolve_index_device", lambda: "cpu")
    yield notes
    settings.set_override(None)


def test_deleted_note_marks_index_stale(env):
    (env / "a.md").write_text("bir")
    (env / "b.md").write_text("iki")
    services.reindex()
    assert not services.notes_changed()
    (env / "b.md").unlink()
    assert services.notes_changed()
    services.reindex()
    assert not services.notes_changed()
