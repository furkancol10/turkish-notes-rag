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
