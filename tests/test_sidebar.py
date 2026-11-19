import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from desktop.sidebar import Sidebar, relative_time  # noqa: E402

app = QApplication.instance() or QApplication([])

CHATS = [{"id": "a", "title": "Birinci", "updated": "2020-01-01T10:00:00", "n_messages": 2},
         {"id": "b", "title": "İkinci", "updated": "2020-01-02T10:00:00", "n_messages": 1}]


def rec(sig):
    got = []
    sig.connect(lambda *a: got.append(a))
    return got


def make():
    s = Sidebar()
    s.set_chats(CHATS)
    return s


def test_simple_signals():
    s = make()
    names = ["new_chat_requested", "settings_requested", "choose_folder_requested",
             "reset_folder_requested", "add_note_requested", "open_folder_requested",
             "reindex_requested", "delete_all_requested"]
    btns = [s.btn_new, s.btn_settings, s.btn_choose, s.btn_reset, s.btn_add, s.btn_open,
            s.btn_reindex, s.btn_delall]
    for n, b in zip(names, btns):
        got = rec(getattr(s, n))
        b.click()
        assert got == [()], n


def test_chats_render_select_delete_current():
    s = make()
    assert len(s._rows) == 2 and s._rows["a"].title_lbl.full_text() == "Birinci"
    assert s.empty_lbl.isHidden()
    sel, dele = rec(s.chat_selected), rec(s.chat_delete_requested)
    s.set_current_chat("b")
    assert s._rows["b"].property("current") is True
    assert s._rows["a"].property("current") is False
    s._rows["a"].selected.emit("a")
    s._rows["a"].del_btn.click()
    assert sel == [("a",)] and dele == [("a",)]
    s.set_chats([])
    assert not s.empty_lbl.isHidden() and s.btn_delall.isHidden()


def test_rename_flow():
    s = make()
    got = rec(s.chat_rename_requested)
    r = s._rows["a"]
    r.start_rename()
    assert not r.edit.isHidden()
    r.edit.setText("Yeni ad")
    r.edit.editingFinished.emit()
    assert got == [("a", "Yeni ad")] and r.edit.isHidden()
    # iptal
    r.start_rename()
    r.edit.setText("x")
    r.cancel_rename()
    r.edit.editingFinished.emit()
    assert len(got) == 1


def test_accordion_and_notes():
    s = make()
    f, n = rec(s.folder_section_toggled), rec(s.notes_list_toggled)
    s.set_notes(["a.md", "b.txt"])
    assert s.count_lbl.text() == "2" and s.notes_toggle.text() == "▸ Notlar (2)"
    assert s.folder_body.isHidden()
    s.folder_head.click()
    assert not s.folder_body.isHidden() and f == [(True,)]
    s.notes_toggle.click()
    assert not s.notes_lbl.isHidden() and n == [(True,)]
    assert s.notes_toggle.text() == "▾ Notlar (2)"
    s.set_folder_section_open(False)  # programatik: sinyal yok
    s.set_notes_list_open(False)
    assert s.folder_body.isHidden() and len(f) == 1 and len(n) == 1


def test_folder_status_busy():
    s = make()
    s.set_folder("/home/x/Notlar", False)
    assert s.folder_name.full_text() == "Notlar" and s.folder_head.toolTip() == "/home/x/Notlar"
    s.set_index_status("12 parça", True)
    assert not s.stale_dot.isHidden() and s.status_lbl.text() == "12 parça"
    s.set_index_status("ok", False)
    assert s.stale_dot.isHidden()
    s.set_busy(True)
    assert not s.btn_reindex.isEnabled() and not s.btn_choose.isEnabled()
    s.set_busy(False)
    assert s.btn_reindex.isEnabled() and s.btn_reindex.text() == "Yeniden indeksle"


def test_relative_time():
    from datetime import datetime
    now = datetime(2024, 5, 10, 15, 0)
    assert relative_time("2024-05-10T14:02:00", now) == "bugün 14:02"
    assert relative_time("2024-05-09T23:00:00", now) == "dün"
    assert relative_time("2024-05-07T01:00:00", now) == "3 gün önce"
