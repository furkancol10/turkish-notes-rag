import os
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _chunk():
    return SimpleNamespace(source="a.pdf", heading="", page=1, text="parça " * 30)


def _make(qapp, width):
    from desktop.chat_view import ChatView
    v = ChatView()
    v.resize(width, 700)
    v.show()
    long_ans = "Bu bir cevap. " * 30 + "https://example.com/" + "a" * 120
    u = v.add("user", "Merhaba nasılsın?")
    a = v.add("assistant", long_ans, [(_chunk(), 0.9)])
    qapp.processEvents()
    return v, u, a


def _check_heights(bubbles):
    from desktop.chat_view import MsgView
    for b in bubbles:
        lab = b._msg
        assert isinstance(lab, MsgView)
        assert lab.height() >= lab.heightForWidth(lab.viewport().width()) - 1
        assert lab.verticalScrollBar().maximum() == 0


@pytest.mark.parametrize("width", [400, 600, 1000, 1600])
def test_chat_responsive(qapp, width):
    v, u, a = _make(qapp, width)
    assert u._msg.height() <= u._msg.fontMetrics().lineSpacing() + 4     # tek satır
    assert u._frame.width() <= 0.78 * v.column_width() + 1 or v.column_width() < 560
    _check_heights([u, a])
    assert v.horizontalScrollBar().maximum() == 0
    tg = a._toggle_btn
    for state in (True, False):
        tg.setChecked(state)
        qapp.processEvents()
        _check_heights([u, a])
    v.resize(width - 150, 700)
    qapp.processEvents()
    _check_heights([u, a])
    assert u._msg.height() <= u._msg.fontMetrics().lineSpacing() + 4
    v.resize(width, 700)
    qapp.processEvents()
    if width == 1600:
        m = v.layout() if False else v._lay.contentsMargins()
        assert abs(m.left() - m.right()) <= 2
        assert v.column_width() <= 820 + 2
        assert m.left() > 100
        assert a._frame.maximumWidth() <= 0.88 * 820 + 1


def test_narrow_full_width(qapp):
    v, u, a = _make(qapp, 400)
    assert v.column_width() < 560
    assert a._frame.maximumWidth() >= v.column_width() - 34 - 1 or a._frame.width() >= v.column_width() - 40


def test_no_zwsp_and_link_intact(qapp):
    from desktop.chat_view import ChatView
    v = ChatView()
    v.resize(500, 700)
    v.show()
    url = "https://example.com/very/long/path/" + "b" * 80
    a = v.add("assistant", f"bak [x]({url}) ve `{'c' * 60}` " + "d" * 70)
    u = v.add("user", "e" * 70)
    qapp.processEvents()
    for b in (a, u):
        assert "\u200b" not in b._msg.toPlainText()
    hrefs = [f.anchorHref() for f in _frags(a._msg.document()) if f.anchorHref()]
    assert hrefs == [url]
    _check_heights([a, u])
    assert v.horizontalScrollBar().maximum() == 0


def _frags(doc):
    from PySide6.QtGui import QTextCursor
    b = doc.begin()
    while b.isValid():
        it = b.begin()
        while not it.atEnd():
            yield it.fragment().charFormat()
            it += 1
        b = b.next()


@pytest.mark.parametrize("width", [400, 600, 1000, 1600])
def test_load_messages_long(qapp, width):
    from desktop.chat_view import ChatView
    v = ChatView()
    v.resize(width, 700)
    v.show()
    msgs = [{"role": "user", "text": "x" * 200},
            {"role": "assistant", "text": "Uzun cevap. " * 60 + "z" * 150}]
    v.load_messages(msgs)
    qapp.processEvents()
    bs = [v._lay.itemAt(i).widget() for i in range(v._lay.count())]
    _check_heights([b for b in bs if b is not None and getattr(b, "_msg", None) is not None])
    assert v.horizontalScrollBar().maximum() == 0
