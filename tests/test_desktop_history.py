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
    monkeypatch.setattr(services, "ask", lambda q, k, b, prior=None: (f"cevap:{q}:{k}:{b}", [(chunk, 0.9)], {"intent": "notes", "query": None}))
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


def test_ask_saved_restart_starts_fresh(env):
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
    # Yeniden açılış: boş yeni sohbetle başlar, eski sohbet listede durur ve açılabilir
    w2 = make()
    wait(w2)
    assert w2.cur["id"] != c["id"] and not w2.cur["messages"]
    assert [x["id"] for x in history.list_chats()] == [c["id"]]
    w2.open_chat(c["id"])
    assert w2.cur["id"] == c["id"]
    assert w2.chat._lay.count() > 2
    # Hiç mesaj yazılmadan kapatılan yeni sohbet kaydedilmez
    w3 = make()
    wait(w3)
    assert len(history.list_chats()) == 1


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


def test_corrupt_files_do_not_crash_startup(env):
    make, wait, _ = env
    from src import history, settings
    d = history.chats_dir()
    d.mkdir(parents=True)
    (d / "bad.json").write_text("{not json")
    (d / "bin.json").write_bytes(b"\xff\xfe\x00")
    (d / "odd.json").write_text('{"id":"odd","updated":5,"title":3,"messages":["x",{"role":"user","text":"s","sources":["z",{"score":"q"}]}]}')
    settings.settings_path().parent.mkdir(parents=True)
    settings.settings_path().write_text('{"top_k": NaN, "last_chat_id": "odd", "backend": 5}')
    w = make()
    wait(w)
    assert 1 <= w.top_k <= 15
    w.open_chat("odd")
    w.open_chat("bad")


def test_inflight_block_and_reenable_after_error(env, monkeypatch):
    make, wait, _ = env
    from src import history
    from desktop import services

    def boom(q, k, b, prior=None):
        raise RuntimeError("x")
    w = make()
    wait(w)
    ask(w, wait, "bir")
    a = w.cur["id"]
    monkeypatch.setattr(services, "ask", boom)
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: None)
    w.input.setText("iki")
    w.send()
    assert w._asking
    w.new_chat()
    w.delete_chat(a)
    w.delete_all_chats()
    assert w.cur["id"] == a and history.load_chat(a)
    wait(w)
    assert not w._asking
    w.new_chat()
    assert w.cur["id"] != a


def test_chat_from_other_folder_opens(env):
    make, wait, _ = env
    from src import history
    c = history.new_chat("/nonexistent/other")
    c["messages"] = [{"role": "user", "text": "s", "sources": []},
                     {"role": "assistant", "text": "**c**", "sources": [
                         {"source": "gone.pdf", "heading": "", "page": 2, "score": 0.5, "text": "t"}]}]
    history.save_chat(c)
    w = make()
    wait(w)
    w.open_chat(c["id"])
    assert w.cur["id"] == c["id"]


def test_query_saved_and_restored(env, monkeypatch):
    make, wait, _ = env
    from desktop import services
    monkeypatch.setattr(services, "ask", lambda q, k, b, prior=None: (
        "c", [], {"intent": "notes", "query": "yeniden yazılmış"}))
    w = make()
    wait(w)
    ask(w, wait, "peki?")
    assert w.cur["messages"][-1]["query"] == "yeniden yazılmış"
    w.chat.load_messages(w.cur["messages"])
    from PySide6.QtWidgets import QLabel
    assert any(l.text() == "Aranan: yeniden yazılmış" for l in w.chat.findChildren(QLabel))
