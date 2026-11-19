import json

import pytest

from src import rewriter
from src.router import is_sources, route

HIST = [{"role": "user", "content": "Re-ranking nasıl çalışır?"},
        {"role": "assistant", "content": "ChatGPT raporuna göre re-ranking, ilk sonuçları yeniden sıralar."}]

SOURCES = ["hangi dosyada bundan bahsetmiş", "Hangi dosyada bundan bahsetmiş?", "hangi dosyada geçiyor",
           "hangi notta geçiyor bu", "hangi belgede yazıyor", "hangi sayfada", "bu hangi sayfada?",
           "bu hangi dosya", "kaynağın ne", "kaynakların neler", "nereden buldun", "nerden buldun bunu",
           "hangi dosyada bundan bahsetmis", "hangi dosyda bahsetmiş", "peki hangi raporda var",
           "bunu hangi dosyada anlatmış", "hangi pdfte yazıyor", "bu hangi nottan geliyor"]


@pytest.mark.parametrize("q", SOURCES)
def test_is_sources(q):
    assert is_sources(q)


@pytest.mark.parametrize("q", SOURCES[:8])
def test_analyze_fast_path_no_llm(q, monkeypatch):
    monkeypatch.setattr(rewriter.ollama, "chat", lambda **k: pytest.fail("LLM çağrıldı"))
    assert rewriter.analyze(q, HIST)["intent"] == "sources"


@pytest.mark.parametrize("q", ["toplantı notları hangi dosyada var", "başka hangi raporda geçiyor", "hangi modeli seçtik",
                               "dosya nasıl açılır", "bu not nasıl eklenir"])
def test_not_sources(q):
    assert not is_sources(q)


def test_route_sources_only_with_history():
    assert route("hangi dosyada bundan bahsetmiş", True) == "sources"
    assert route("hangi dosyada bundan bahsetmiş") == "notes"


def test_no_history_rule_path(monkeypatch):
    monkeypatch.setattr(rewriter.ollama, "chat", lambda **k: pytest.fail("LLM çağrıldı"))
    assert rewriter.analyze("nasılsın", []) == {"intent": "meta", "query": "nasılsın"}
    assert rewriter.analyze("rag nedir", []) == {"intent": "notes", "query": "rag nedir"}


def test_meta_fast_path_with_history(monkeypatch):
    monkeypatch.setattr(rewriter.ollama, "chat", lambda **k: pytest.fail("LLM çağrıldı"))
    assert rewriter.analyze("kimsin sen", HIST)["intent"] == "meta"


def _chat(content, calls=None, exc=None):
    def f(**kw):
        if calls is not None:
            calls.append(kw)
        if exc:
            raise exc
        return {"message": {"content": content}}
    return f


def test_llm_intent_preserving_query(monkeypatch):
    calls = []
    out = json.dumps({"intent": "notes", "query": "Re-ranking hangi raporlarda geçiyor?"})
    monkeypatch.setattr(rewriter.ollama, "chat", _chat(out, calls))
    r = rewriter.analyze("başka hangi raporda geçiyor?", HIST)
    assert r == {"intent": "notes", "query": "Re-ranking hangi raporlarda geçiyor?"}
    assert len(calls) == 1 and calls[0]["options"]["temperature"] == 0 and calls[0]["think"] is False


def test_llm_followup_keeps_question(monkeypatch):
    monkeypatch.setattr(rewriter.ollama, "chat", _chat('{"intent":"followup","query":"x y z"}'))
    assert rewriter.analyze("doğru mu?", HIST) == {"intent": "followup", "query": "doğru mu?"}


def test_json_with_noise(monkeypatch):
    monkeypatch.setattr(rewriter.ollama, "chat",
                        _chat('```json\n{"intent": "Sources", "query": "Re-ranking hangi dosyada geçiyor?"}\n```'))
    assert rewriter.analyze("peki bu nerede duruyor", HIST)["intent"] == "sources"


@pytest.mark.parametrize("bad", ["not json", "", '{"intent":"zzz","query":"a?"}', '{"intent":"notes"}',
                                 '{"intent":"notes","query":""}', "[1,2]"])
def test_invalid_falls_back(monkeypatch, bad):
    monkeypatch.setattr(rewriter.ollama, "chat", _chat(bad))
    r = rewriter.analyze("doğru mu?", HIST)  # fallback: kural route -> followup
    assert r["intent"] == "followup"


def test_exception_falls_back_never_raises(monkeypatch):
    monkeypatch.setattr(rewriter.ollama, "chat", _chat(None, exc=TimeoutError("x")))
    r = rewriter.analyze("peki gemini?", HIST)
    assert r == {"intent": "notes", "query": "peki gemini?"}


# --- followup güvenlik kapısı (yeni içerik sözcüğü) ---
from src.router import has_new_content  # noqa: E402

ANS = "Atlas'ın teslim tarihi 15 Mart, bütçesi 80 bin TL; ana risk veritabanı geçişi."


@pytest.mark.parametrize("q", ["peki kira?", "ya ekip büyüklüğü?", "onun bütçesi ne?", "ya teslim tarihi?",
                               "çarşamba günü ne kadardı", "network için ne yazmıştım", "Kimler katıldı?",
                               "peki veritabanı?",  # önceki cevapta geçse de takip işareti yok
                               "özetle ama Docker'ı da ekle"])
def test_new_content_detected(q):
    assert has_new_content(q, ANS)


@pytest.mark.parametrize("q", ["doğru mu?", "kısaca anlat", "bunu madde madde yaz", "ilkini açıkla", "özetini çıkar",
                               "bunu neden böyle sıraladın", "yazdığın şey doğru mu", "Üçüncüsünü anlat.",
                               "bu geçişi kısalt", "neden veritabanı?"])
def test_no_new_content(q):
    assert not has_new_content(q, ANS)


def test_guard_flips_llm_followup_to_notes(monkeypatch):
    monkeypatch.setattr(rewriter.ollama, "chat",
                        _chat('{"intent":"followup","query":"Re-ranking maliyeti nedir?"}'))
    assert rewriter.analyze("ya maliyeti?", HIST) == {"intent": "notes", "query": "Re-ranking maliyeti nedir?"}


def test_followup_rule_skips_llm(monkeypatch):
    calls = []
    monkeypatch.setattr(rewriter.ollama, "chat", _chat('{"intent":"notes","query":"x y z?"}', calls))
    assert rewriter.analyze("özetini çıkar", HIST) == {"intent": "followup", "query": "özetini çıkar"}
    assert not calls


@pytest.mark.parametrize("q", ["sayfa kaçta", "bunları hangi notta tutmuşum", "kaçıncı sayfada"])
def test_new_sources_rules(q):
    assert is_sources(q)


ANS2 = ("Proje Nova bütçesi 500 bin TL'dir. Ofis kirası ayda 20 bin TL, İstanbul'da. "
        "Re-ranking ilk sonuçları yeniden sıralar [1].")


@pytest.mark.parametrize("q", ["kirası ne kadar", "kira neden bu kadar yüksek", "teslim tarihini kısalt",
                               "peki personel maaşları", "Ankara'yı açıkla", "maliyetini kısalt",
                               "bütçesi neden 600 bin", "ilk sonuçların maliyeti", "bütçesini neden artırdık"])
def test_guard_adversarial_new_content(q):
    assert has_new_content(q, ANS2)


@pytest.mark.parametrize("q", ["bütçesini kısalt", "bütçesini kısaca anlat", "re-ranking'i açıkla",
                               "sen emin misin", "bunu tabloya dök", "İstanbul'u açıkla", "daha kısa yaz",
                               "ilk sonuçları açıkla"])
def test_guard_adversarial_no_new_content(q):
    assert not has_new_content(q, ANS2)
