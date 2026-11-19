import pytest

from src import rewriter

HIST = [{"role": "user", "content": "chatgpt hangi RAG projelerini önermiş"},
        {"role": "assistant", "content": "ChatGPT raporunda 1. Belge asistanı 2. Kod arama önerilmiş."}]


def fake(content=None, exc=None, calls=None):
    def chat(**kw):
        if calls is not None:
            calls.append(kw)
        if exc:
            raise exc
        return {"message": {"content": content}}
    return chat


@pytest.mark.parametrize("q", ["peki gemini?", "ilki ne zorlukta", "bunu açıkla", "2. madde nedir",
                               "onun maliyeti ne", "hangisi daha kolay", "ya claude"])
def test_needs_rewrite_true(q):
    assert rewriter.needs_rewrite(q, HIST)


@pytest.mark.parametrize("q", ["Gemini raporunda hangi RAG projeleri önerilmiş", "docker kurulumu nasıl yapılır",
                               "bge-m3 modelinin vektör boyutu kaç"])
def test_needs_rewrite_false(q):
    assert not rewriter.needs_rewrite(q, HIST)


def test_needs_rewrite_no_history():
    assert not rewriter.needs_rewrite("peki gemini?", [])


def test_condense_normal(monkeypatch):
    calls = []
    monkeypatch.setattr(rewriter.ollama, "chat",
                        fake('"Soru: Gemini raporunda hangi RAG projeleri önerilmiş?"', calls=calls))
    out = rewriter.condense("peki gemini?", HIST)
    assert out == "Gemini raporunda hangi RAG projeleri önerilmiş?"
    assert calls[0]["think"] is False
    assert calls[0]["options"]["temperature"] == 0 and calls[0]["options"]["num_predict"] == 64


def test_condense_error_fallback(monkeypatch):
    monkeypatch.setattr(rewriter.ollama, "chat", fake(exc=TimeoutError("x")))
    assert rewriter.condense("peki gemini?", HIST) == "peki gemini?"


@pytest.mark.parametrize("garbage", ["", "   ", "Gemini raporunda şu projeler önerilmiş: belge asistanı, kod arama, not özetleyici ve çok daha fazlası burada yazıyor.",
                                     "Evet, Gemini belge asistanı önermiş."])
def test_condense_garbage_fallback(monkeypatch, garbage):
    monkeypatch.setattr(rewriter.ollama, "chat", fake(garbage))
    assert rewriter.condense("peki gemini?", HIST) == "peki gemini?"


def test_condense_no_history_passthrough(monkeypatch):
    monkeypatch.setattr(rewriter.ollama, "chat", fake(exc=AssertionError("çağrılmamalı")))
    assert rewriter.condense("peki gemini?", []) == "peki gemini?"


def test_condense_skips_llm_when_self_contained(monkeypatch):
    monkeypatch.setattr(rewriter.ollama, "chat", fake(exc=AssertionError("çağrılmamalı")))
    q = "docker kurulumu nasıl yapılır"
    assert rewriter.condense(q, HIST) == q
