"""Gizli kabul testleri: atıf numaralarını göster ayarı (yalnız zorunlu arayüz)."""
import json

import pytest

from src import settings
from src.sources import display_text, strip_citations


@pytest.fixture(autouse=True)
def xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert str(tmp_path) in str(settings.settings_path())


# ---- strip_citations: temizlenenler ----
@pytest.mark.parametrize("src,want", [
    ("önerdi [3].", "önerdi."),
    ("A [1, 2] ve B [2-4] dedi.", "A ve B dedi."),
    ("X [1][2]", "X"),
    ("X [1][2] Y", "X Y"),
    ("A [1] B", "A B"),
    ("X [2–4].", "X."),
    ("X [1; 3] oldu", "X oldu"),
    ("dedi [1], sonra [2]; son [3]!", "dedi, sonra; son!"),
    ("Kod `a[1]` açıkladı [2].", "Kod `a[1]` açıkladı."),
    ("```\na[1]\n```\nSonuç [1].", "```\na[1]\n```\nSonuç."),
    ("Bkz [kaynak](http://a.b/1) ve notlar [4].", "Bkz [kaynak](http://a.b/1) ve notlar."),
    ("- [x] bitti [1]\n- [ ] kaldı", "- [x] bitti\n- [ ] kaldı"),
])
def test_strip_removes_citations(src, want):
    assert strip_citations(src) == want


# ---- strip_citations: dokunmaz kuralları ----
@pytest.mark.parametrize("src", [
    "[metin](http://x.com/a)",
    "Bkz [kaynak](http://a.b/1).",
    "- [ ] görev",
    "- [x] görev",
    "Bu [not] önemli.",
    "Kod: `a[1]` böyle.",
    "```\nx = a[1]\nprint(b[2])\n```",
    "dizi a[1] ve b[2]",
    "x2[3] değeri",
    "Merhaba dünya.",
    "",
])
def test_strip_leaves_untouched(src):
    assert strip_citations(src) == src


# ---- biçim koruma ----
def test_line_breaks_preserved():
    assert strip_citations("Birinci [1]\n\nİkinci [2]\nÜçüncü") == "Birinci\n\nİkinci\nÜçüncü"


def test_citation_at_line_start_removed():
    out = strip_citations("Satır bir.\n[2] Satır iki.")
    assert "[2]" not in out
    lines = out.split("\n")
    assert len(lines) == 2 and lines[0] == "Satır bir." and lines[1].strip() == "Satır iki."
    assert "  " not in out


def test_markdown_formatting_preserved():
    src = "**Kalın** metin [1]\n- madde *a* [2]\n- madde `b`"
    assert strip_citations(src) == "**Kalın** metin\n- madde *a*\n- madde `b`"


def test_no_double_space_or_space_before_punct():
    out = strip_citations("Bir [1] iki [2], üç [3]. Dört [1, 2]; beş [4]!")
    assert "  " not in out
    for p in ",.;!":
        assert " " + p not in out
    assert "[" not in out


def test_idempotent():
    s = "A [1] ve B [2-3][4]."
    once = strip_citations(s)
    assert strip_citations(once) == once == "A ve B."


# ---- settings ----
def test_show_citations_default_true():
    assert settings.get_show_citations() is True


def test_show_citations_roundtrip():
    settings.set_show_citations(False)
    assert settings.get_show_citations() is False
    settings.set_show_citations(True)
    assert settings.get_show_citations() is True


def test_show_citations_persisted_in_settings_file():
    settings.set_show_citations(False)
    data = json.loads(settings.settings_path().read_text(encoding="utf-8"))
    assert data["show_citations"] is False


def test_show_citations_read_from_existing_file():
    p = settings.settings_path()
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"show_citations": False, "top_k": 4}), encoding="utf-8")
    assert settings.get_show_citations() is False
    assert settings.get_top_k() == 4


def test_show_citations_does_not_clobber_other_settings():
    settings.set_top_k(7)
    settings.set_show_citations(False)
    assert settings.get_top_k() == 7


# ---- display_text ----
TEXT = "A [1, 2] ve B [2-4] dedi.\n- [ ] görev `a[1]`"


def test_display_text_on_returns_verbatim():
    settings.set_show_citations(True)
    assert display_text(TEXT) == TEXT


def test_display_text_default_returns_verbatim():
    assert display_text(TEXT) == TEXT


def test_display_text_off_strips():
    settings.set_show_citations(False)
    assert display_text(TEXT) == strip_citations(TEXT) == "A ve B dedi.\n- [ ] görev `a[1]`"


def test_display_text_follows_toggle_back_on():
    settings.set_show_citations(False)
    assert "[1" not in display_text("X [1]")
    settings.set_show_citations(True)
    assert display_text("X [1]") == "X [1]"
