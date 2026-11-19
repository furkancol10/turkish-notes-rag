import os
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication([])
    from desktop import main as m, services
    chunk = SimpleNamespace(source="a.pdf", heading="", page=3, text="parça metni")
    monkeypatch.setattr(services, "ask", lambda q, k, b: (f"cevap:{q}:{k}:{b}", [(chunk, 0.9)]))
    monkeypatch.setattr(services, "load_embed_model", lambda: None)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    wins = []

    def make():
        w = m.MainWindow()
        wins.append(w)
        return w

    def wait(w):
        while w._workers:
            for x in list(w._workers):
                x.wait()
            app.processEvents()
        app.processEvents()
    yield make, wait, app
    for w in wins:
        w.close()


def ask(w, wait, q):
    w.input.setText(q)
    w.send()
    wait(w)


def test_ask_saved_restart_restores(env):
    make, wait, _ = env
    from src import history, settings
    w = make()
    wait(w)
    w.top_k, w.backend = 7, "chroma"
    ask(w, wait, "Merhaba nedir")
    cs = history.list_chats()
    assert len(cs) == 1 and cs[0]["title"] == "Merhaba nedir"
    c = history.load_chat(cs[0]["id"])
    assert [m["role"] for m in c["messages"]] == ["user", "assistant"]
    assert c["messages"][1]["text"] == "cevap:Merhaba nedir:7:chroma"
    assert c["messages"][1]["sources"][0]["page"] == 3
    assert settings.get_last_chat_id() == c["id"]
    w2 = make()
    wait(w2)
    assert w2.cur["id"] == c["id"]
    assert w2.chat._lay.count() > 2


def test_empty_chat_not_saved_and_new_chat(env):
    make, wait, _ = env
    from src import history
    w = make()
    wait(w)
    w.new_chat()
    assert history.list_chats() == []
    ask(w, wait, "bir")
    first = w.cur["id"]
    w.new_chat()
    assert w.cur["id"] != first and w.chat._lay.count() == 2
    ask(w, wait, "iki")
    assert len(history.list_chats()) == 2
    w.open_chat(first)
    assert w.cur["id"] == first and w.chat._lay.count() == 4


def test_delete_rename_delete_all(env):
    make, wait, _ = env
    from src import history, settings
    w = make()
    wait(w)
    ask(w, wait, "bir")
    a = w.cur["id"]
    w.new_chat()
    ask(w, wait, "iki")
    b = w.cur["id"]
    w.rename_chat(a, "Yeni ad")
    assert history.load_chat(a)["title"] == "Yeni ad"
    w.delete_chat(b)
    assert [c["id"] for c in history.list_chats()] == [a] and w.cur["id"] != b
    assert settings.get_last_chat_id() is None
    w.delete_all_chats()
    assert history.list_chats() == []


def test_settings_persist(env, monkeypatch):
    make, wait, _ = env
    from src import settings
    from desktop import main as m
    w = make()
    wait(w)
    monkeypatch.setattr(m.SettingsDialog, "exec", lambda self: (self.top_k.setValue(9),
                        self._set_backend("chroma"), 1)[-1])
    w.open_settings()
    assert (settings.get_top_k(), settings.get_backend()) == (9, "chroma")
    w2 = make()
    assert (w2.top_k, w2.backend) == (9, "chroma")
    w.side.set_folder_section_open(True, emit=True)
    assert settings.get_folder_section_open() is True
