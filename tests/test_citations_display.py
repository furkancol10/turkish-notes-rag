import json
import os
from types import SimpleNamespace

import pytest

from src import history, settings
from src.sources import answer_sources, display_text, strip_citations


@pytest.mark.parametrize("raw,expected", [
    ("önerdi [3].", "önerdi."),
    ("A [1, 2] ve B [2-4] dedi.", "A ve B dedi."),
    ("X [1][2]", "X"),
    ("X [1] [2]", "X"),
    ("X [1], [2].", "X."),
    ("A [1], B [2].", "A, B."),
    ("A [1]; B [2-4].", "A; B."),
    ("A [1–3] ve B [1; 2] dedi.", "A ve B dedi."),
    ("önerdi [3] .", "önerdi."),
    ("A  [1]  B", "A B"),
    ("(önerdi [3])", "(önerdi)"),
    ("**kalın [1]** ve _italik_ [2].", "**kalın** ve _italik_."),
    ("[1] İlk cümle.", "İlk cümle."),
    ("[1][2] Başta atıf.", "Başta atıf."),
    ("  [1] Girintili satır [2].", "  Girintili satır."),
    ("- [1] Madde [2]\n- İkinci [3].", "- Madde\n- İkinci."),
    ("Satır 1 [1]\n\nSatır 2 [2].", "Satır 1\n\nSatır 2."),
    ("[1]\nSonraki satır", "\nSonraki satır"),
    ("[1]", ""),
    ("", ""),
    ("Atıfsız metin.  İki boşluk korunur.", "Atıfsız metin.  İki boşluk korunur."),
])
def test_strip_citations_basic(raw, expected):
    assert strip_citations(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("Bak [metin](https://example.com) [1].", "Bak [metin](https://example.com)."),
    ("Bağlantı [1](https://example.com) burada [2].", "Bağlantı [1](https://example.com) burada."),
    ("- [ ] yapılacak [1]\n- [x] tamamlandı [2]", "- [ ] yapılacak\n- [x] tamamlandı"),
    ("Bu [not] ve [1a] kalmalı [2].", "Bu [not] ve [1a] kalmalı."),
    ("Dizi a[1] ve matris m[0][1] ve 2[3] kalmalı [4].", "Dizi a[1] ve matris m[0][1] ve 2[3] kalmalı."),
    ("Bitişik nokta.[1] kalmalı.", "Bitişik nokta.[1] kalmalı."),
    ("Satır içi `a[1]` ve `[2]` kalmalı [3].", "Satır içi `a[1]` ve `[2]` kalmalı."),
    ("Çift tırnak ``a ` [1]`` ve `x` [2].", "Çift tırnak ``a ` [1]`` ve `x`."),
    ("Kod bitişik `x`[1] kalmalı.", "Kod bitişik `x`[1] kalmalı."),
    ("Önce [1].\n```python\nx = a[1]\n# [2]\n[3] satır başı\n```\nSonra [4].",
     "Önce.\n```python\nx = a[1]\n# [2]\n[3] satır başı\n```\nSonra."),
    ("```\n[1]\n```", "```\n[1]\n```"),
    ("```py\na = [1]\n```\nArada [2].\n```js\nb = [3]\n```",
     "```py\na = [1]\n```\nArada.\n```js\nb = [3]\n```"),
])
def test_strip_citations_preserves_non_citations(raw, expected):
    assert strip_citations(raw) == expected


def test_settings_show_citations_persistence(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    assert settings.get_show_citations() is True
    assert settings.set_show_citations(False) is None
    assert settings.get_show_citations() is False
    raw = json.loads(settings.settings_path().read_text(encoding="utf-8"))
    assert raw["show_citations"] is False
    settings.set_show_citations(True)
    assert settings.get_show_citations() is True
    # Bozuk (bool olmayan) değer varsayılana (True) düşer
    settings.settings_path().write_text('{"show_citations": "false"}', encoding="utf-8")
    assert settings.get_show_citations() is True


def test_display_text_respects_setting(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    s = "Not bunu önerdi [1, 2]."
    assert display_text(s) == s
    settings.set_show_citations(False)
    assert display_text(s) == "Not bunu önerdi."
    settings.set_show_citations(True)
    assert display_text(s) == s


def test_desktop_chat_view_and_history_citations(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from desktop import main as m, services
    from desktop.chat_view import Bubble

    chunk = SimpleNamespace(source="not.pdf", heading="Bölüm", page=2, text="parça")
    monkeypatch.setattr(services, "load_embed_model", lambda: None)
    monkeypatch.setattr(
        services, "ask",
        lambda q, k, b, prior=None, *th: ("Bunu önerdi [1].", [(chunk, 0.9)], {"intent": "notes", "query": None}),
    )

    settings.set_show_citations(False)
    win = m.MainWindow()
    try:
        while win._workers:
            for w in list(win._workers):
                w.wait()
            app.processEvents()

        win.input.setText("Madde [1] nedir?")
        win.send()
        while win._workers:
            for w in list(win._workers):
                w.wait()
            app.processEvents()
        app.processEvents()

        bubbles = [win.chat._lay.itemAt(i).widget() for i in range(win.chat._lay.count())]
        bubbles = [b for b in bubbles if isinstance(b, Bubble)]
        assert len(bubbles) == 2
        # Kullanıcı mesajı değişmez, asistan mesajında atıf gizlenir
        assert "[1]" in bubbles[0]._msg.toPlainText()
        assert bubbles[1]._msg.toPlainText() == "Bunu önerdi."
        # Kaynaklar düğmesi eskisi gibi var
        assert bubbles[1]._toggle_btn is not None
        assert "Kaynakları göster (1)" in bubbles[1]._toggle_btn.text()

        # Kayıtlı geçmişte orijinal metin saklanır; kaynak sorusu çalışır
        saved = history.load_chat(win.cur["id"])
        assert saved["messages"][1]["text"] == "Bunu önerdi [1]."
        src_ans = answer_sources(saved["messages"][1]["text"], saved["messages"][1]["sources"])
        assert "not.pdf" in src_ans and "s. 2" in src_ans

        # Ayar kapalıyken kayıtlı sohbeti yeniden aç: yine gizli
        win.open_chat(win.cur["id"])
        bubbles = [b for i in range(win.chat._lay.count())
                   if isinstance((b := win.chat._lay.itemAt(i).widget()), Bubble)]
        assert bubbles[1]._msg.toPlainText() == "Bunu önerdi."

        # Ayarı arayüzden aç: anında geri gelir ve kalıcı olur
        monkeypatch.setattr(m.SettingsDialog, "exec",
                            lambda self: (self.show_citations.setChecked(True), 1)[-1])
        win.open_settings()
        assert settings.get_show_citations() is True
        assert bubbles[1]._msg.toPlainText() == "Bunu önerdi [1]."

        # Tekrar açıldığında numaralar görünür
        win.open_chat(win.cur["id"])
        bubbles = [b for i in range(win.chat._lay.count())
                   if isinstance((b := win.chat._lay.itemAt(i).widget()), Bubble)]
        assert bubbles[1]._msg.toPlainText() == "Bunu önerdi [1]."
    finally:
        win.close()
