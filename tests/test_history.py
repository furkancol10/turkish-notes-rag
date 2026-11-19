import time
from types import SimpleNamespace

import pytest

from src import history, settings, config


@pytest.fixture(autouse=True)
def xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))


def _chat(text="Merhaba dünya"):
    c = history.new_chat("/x")
    c["messages"].append({"role": "user", "text": text, "sources": []})
    return c


def test_roundtrip_and_title():
    c = _chat()
    history.save_chat(c)
    got = history.load_chat(c["id"])
    assert got["title"] == "Merhaba dünya" and got["messages"] == c["messages"]


def test_ordering_and_empty_skipped():
    a, b = _chat("a"), _chat("b")
    history.save_chat(a)
    time.sleep(1.1)
    history.save_chat(b)
    e = history.new_chat("/x")
    history.save_chat(e)
    ids = [c["id"] for c in history.list_chats()]
    assert ids == [b["id"], a["id"]]
    assert history.list_chats()[0]["n_messages"] == 1


def test_delete_rename_delete_all():
    a, b = _chat("a"), _chat("b")
    history.save_chat(a); history.save_chat(b)
    history.rename_chat(a["id"], "Yeni")
    assert history.load_chat(a["id"])["title"] == "Yeni"
    history.delete_chat(a["id"])
    assert history.load_chat(a["id"]) is None
    history.delete_all()
    assert history.list_chats() == []


def test_corrupt_and_traversal():
    c = _chat(); history.save_chat(c)
    (history.chats_dir() / f"{c['id']}.json").write_text("{bozuk")
    assert history.load_chat(c["id"]) is None
    assert history.list_chats() == []
    assert history.load_chat("../../etc/passwd") is None
    history.delete_chat("../x")
    with pytest.raises(ValueError):
        history.save_chat({"id": "../evil", "messages": []})


def test_title_from():
    assert history.title_from("kısa\nikinci") == "kısa"
    t = history.title_from("bu oldukça uzun bir soru cümlesidir ve kesilmelidir")
    assert t.endswith("…") and len(t) <= 41 and " …" not in t


def test_sources_from_results():
    ch = SimpleNamespace(source="a.md", heading="H", text="t")
    r = history.sources_from_results([(ch, 0.5)])
    assert r == [{"source": "a.md", "heading": "H", "page": None, "score": 0.5, "text": "t"}]


def test_settings_typed(tmp_path):
    assert settings.get_top_k() == config.TOP_K
    assert settings.set_top_k(99) == 15 and settings.get_top_k() == 15
    assert settings.set_top_k(0) == 1
    assert settings.get_backend() == config.INDEX_BACKEND
    settings.set_backend("numpy"); assert settings.get_backend() == "numpy"
    with pytest.raises(ValueError):
        settings.set_backend("x")
    assert settings.get_last_chat_id() is None
    settings.set_last_chat_id("abc"); assert settings.get_last_chat_id() == "abc"
    settings.set_last_chat_id(None); assert settings.get_last_chat_id() is None
    assert settings.get_folder_section_open() is False
    settings.set_folder_section_open(True); assert settings.get_folder_section_open() is True


def test_settings_corrupt():
    p = settings.settings_path(); p.parent.mkdir(parents=True)
    p.write_text("zzz")
    assert settings.get_top_k() == config.TOP_K


def test_threshold_settings_clamp(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert settings.get_score_threshold() == 0.40 and settings.get_threshold_enabled() is True
    assert settings.set_score_threshold(7) == 1.0 and settings.set_score_threshold(-1) == 0.0
    settings.set_score_threshold(0.5); assert settings.get_score_threshold() == 0.5
    settings.set_threshold_enabled(False); assert settings.get_threshold_enabled() is False
