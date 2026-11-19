"""services.ask hattı: LLM ve arama taklit edilir."""
from types import SimpleNamespace

import pytest

from desktop import services
from src import conversation

CH = SimpleNamespace(id="a.md#0", source="a.md", heading="H", page=0, text="Bütçe 450 bin TL")
SRC = [{"source": "nova.md", "heading": "Bütçe", "page": None, "score": 0.9, "text": "Bütçe 450 bin TL"}]
PRIOR = [
    {"role": "user", "text": "Proje Nova bütçesi nedir?", "sources": []},
    {"role": "assistant", "text": "450 bin TL.", "sources": SRC},
]


@pytest.fixture
def calls(monkeypatch):
    c = {}
    monkeypatch.setattr(services, "load_embed_model", lambda: None)
    monkeypatch.setattr(services, "index_status", lambda: object())
    monkeypatch.setattr(services, "answer_meta", lambda q: "meta")

    def fu(q, h, s):
        c["fu"] = (q, h, s)
        return "takip"
    monkeypatch.setattr(services, "answer_followup", fu)
    monkeypatch.setattr(services, "condense", lambda q, h: c.setdefault("cond", "Nova teslim tarihi"))

    def ret(q, k, backend):
        c["ret"] = q
        return [(CH, 0.8)]
    monkeypatch.setattr(services, "retrieve", ret)

    def ans(q, results, history=None):
        c["ans"] = (q, results, history)
        return "cevap"
    monkeypatch.setattr(services, "answer", ans)
    return c


def test_meta(calls):
    assert services.ask("merhaba", 5, "numpy", [])[2]["route"] == "meta"
    assert "ret" not in calls


def test_first_question_no_condense(calls):
    ans, res, info = services.ask("Proje Nova bütçesi nedir?", 5, "numpy", [])
    assert calls["ret"] == "Proje Nova bütçesi nedir?" and "cond" not in calls
    assert info == {"route": "notes", "query": "Proje Nova bütçesi nedir?"}


def test_condense_used_for_retrieval(calls, monkeypatch):
    monkeypatch.setattr(services, "route", lambda q, h=False: "notes")
    ans, res, info = services.ask("peki teslim tarihi?", 5, "numpy", PRIOR)
    assert calls["ret"] == "Nova teslim tarihi"
    assert info["query"] == "Nova teslim tarihi"
    assert calls["ans"][0] == "peki teslim tarihi?"       # LLM'e orijinal soru gider
    assert calls["ans"][2][0]["role"] == "user"


def test_followup_reuses_sources(calls, monkeypatch):
    monkeypatch.setattr(services, "route", lambda q, h=False: "followup")
    ans, res, info = services.ask("doğru mu?", 5, "numpy", PRIOR)
    assert ans == "takip" and calls["fu"][2] == SRC and "ret" not in calls
    assert res[0][0].source == "nova.md" and res[0][1] == 0.9
    assert info == {"route": "followup", "query": None}


def test_budget_respected(calls, monkeypatch):
    monkeypatch.setattr(services, "route", lambda q, h=False: "notes")
    big = [{"role": "user", "text": "x " * 3000, "sources": []},
           {"role": "assistant", "text": "y " * 3000, "sources": []}]
    services.ask("soru", 5, "numpy", big)
    _, results, hist = calls["ans"]
    total = sum(conversation.approx_tokens(h["content"]) for h in hist)
    assert total < 3000


def test_ask_error_kinds(calls, monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("connect")
    monkeypatch.setattr(services, "answer", boom)
    with pytest.raises(services.AskError) as e:
        services.ask("soru", 5, "numpy", [])
    assert e.value.kind == "ollama"


def test_followup_without_sources_falls_back_to_search(calls):
    prior = [{"role": "user", "text": "merhaba", "sources": []},
             {"role": "assistant", "text": "Selam!", "sources": []}]
    ans, res, info = services.ask("doğru mu?", 5, "numpy", prior)
    assert info["route"] == "notes" and "fu" not in calls and "ret" in calls
