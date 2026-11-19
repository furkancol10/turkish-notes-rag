import re
import numpy as np
import pytest

from src import config, pipeline, settings
from src.formats import NO_NOTES_MSG
from src.index import NumpyIndex, ChromaIndex, index_name


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setattr(config, "INDEX_DIR", tmp_path / "idx")
    notes = tmp_path / "notes"
    notes.mkdir()
    settings.set_override(str(notes))
    monkeypatch.setattr(pipeline, "embed_passages",
                        lambda texts: np.ones((len(texts), 4), dtype="float32") / 2)
    monkeypatch.setattr(pipeline, "release_index_model", lambda: None)
    monkeypatch.setattr(pipeline, "unload_llm", lambda: None)
    monkeypatch.setattr(pipeline, "resolve_index_device", lambda: "cpu")
    yield notes
    settings.set_override(None)


def _name():
    return index_name(config.EMBED_MODEL, config.CHUNK_STRATEGY, config.CHUNK_SIZE)


def test_report_counts_and_skipped(env):
    (env / "a.md").write_text("merhaba dunya")
    (env / "b.txt").write_text("ikinci not")
    (env / "x.xyz").write_text("desteklenmez")
    r = pipeline.build_index()
    assert (r.n_docs, r.n_chunks) == (2, 2)
    assert "2 dosya" in r.summary()
    assert r.n_skipped >= 1


def test_empty_folder_raises(env):
    with pytest.raises(ValueError, match="Klasör"):
        pipeline.build_index()


def test_empty_notes_keep_old_index(env):
    (env / "a.md").write_text("merhaba dunya")
    pipeline.build_index()
    (env / "a.md").write_text("   \n")
    with pytest.raises(ValueError, match=re.escape(NO_NOTES_MSG)):
        pipeline.build_index()
    assert list(NumpyIndex(_name()).doc_titles()) == ["a.md"]
    assert ChromaIndex(_name()).client.get_collection(_name()).count() == 1


def test_failure_midway_keeps_old_index(env, monkeypatch):
    (env / "a.md").write_text("merhaba dunya")
    pipeline.build_index()
    (env / "b.md").write_text("yeni")

    def boom(self, chunks, vecs):
        raise RuntimeError("chroma coktu")
    monkeypatch.setattr(ChromaIndex, "build", boom)
    with pytest.raises(RuntimeError):
        pipeline.build_index()
    assert list(NumpyIndex(_name()).doc_titles()) == ["a.md"]


def test_numpy_build_failure_keeps_old(env, monkeypatch):
    (env / "a.md").write_text("merhaba dunya")
    pipeline.build_index()
    (env / "b.md").write_text("yeni")
    monkeypatch.setattr(np, "save", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError):
        pipeline.build_index()
    assert list(NumpyIndex(_name()).doc_titles()) == ["a.md"]


def test_deleted_note_leaves_index(env):
    (env / "a.md").write_text("bir")
    (env / "b.md").write_text("iki")
    pipeline.build_index()
    (env / "b.md").unlink()
    pipeline.build_index()
    assert list(NumpyIndex(_name()).doc_titles()) == ["a.md"]
    assert list(ChromaIndex(_name()).doc_titles()) == ["a.md"]
