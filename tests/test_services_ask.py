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


def route_(q, h):
    return "meta" if q == "merhaba" else "notes"


def set_an(monkeypatch, intent, query=None):
    monkeypatch.setattr(services, "analyze", lambda q, h: {"intent": intent, "query": query or q})


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
    monkeypatch.setattr(services, "analyze", lambda q, h: c.setdefault("an", {"intent": route_(q, h), "query": q}))

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
    assert services.ask("merhaba", 5, "numpy", [])[2]["intent"] == "meta"
    assert "ret" not in calls


def test_first_question_no_condense(calls):
    ans, res, info = services.ask("Proje Nova bütçesi nedir?", 5, "numpy", [])
    assert calls["ret"] == "Proje Nova bütçesi nedir?"
    assert info == {"intent": "notes", "query": None}


def test_condense_used_for_retrieval(calls, monkeypatch):
    set_an(monkeypatch, "notes", "Nova teslim tarihi")
    ans, res, info = services.ask("peki teslim tarihi?", 5, "numpy", PRIOR)
    assert calls["ret"] == "Nova teslim tarihi"
    assert info["query"] == "Nova teslim tarihi"
    assert calls["ans"][0] == "peki teslim tarihi?"       # LLM'e orijinal soru gider
    assert calls["ans"][2][0]["role"] == "user"


def test_followup_reuses_sources(calls, monkeypatch):
    set_an(monkeypatch, "followup")
    ans, res, info = services.ask("doğru mu?", 5, "numpy", PRIOR)
    assert ans == "takip" and calls["fu"][2] == SRC and "ret" not in calls
    assert res[0][0].source == "nova.md" and res[0][1] == 0.9
    assert info == {"intent": "followup", "query": None}


def test_budget_respected(calls, monkeypatch):
    set_an(monkeypatch, "notes")
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


def test_followup_without_sources_falls_back_to_search(calls, monkeypatch):
    set_an(monkeypatch, "followup")
    prior = [{"role": "user", "text": "merhaba", "sources": []},
             {"role": "assistant", "text": "Selam!", "sources": []}]
    ans, res, info = services.ask("doğru mu?", 5, "numpy", prior)
    assert info["intent"] == "notes" and "fu" not in calls and "ret" in calls


SRC2 = SRC + [{"source": "b.md", "heading": "Ek", "page": 3, "score": 0.5, "text": "x"}]
PRIOR2 = [PRIOR[0], {"role": "assistant", "text": "450 bin TL [1].", "sources": SRC2}]


def test_sources_cited_only(calls, monkeypatch):
    set_an(monkeypatch, "sources")
    ans, res, info = services.ask("hangi dosyada?", 5, "numpy", PRIOR2)
    assert "nova.md" in ans and "b.md" not in ans
    assert [r[0].source for r in res] == ["nova.md"]
    assert "ret" not in calls and "fu" not in calls and "ans" not in calls
    assert info == {"intent": "sources", "query": None}


def test_sources_without_citations_lists_all(calls, monkeypatch):
    set_an(monkeypatch, "sources")
    prior = [PRIOR[0], {"role": "assistant", "text": "450 bin TL.", "sources": SRC2}]
    ans, res, _ = services.ask("hangi dosyada?", 5, "numpy", prior)
    assert "nova.md" in ans and "b.md" in ans and len(res) == 2


def test_sources_without_previous_sources_falls_back(calls, monkeypatch):
    set_an(monkeypatch, "sources")
    prior = [{"role": "user", "text": "merhaba", "sources": []},
             {"role": "assistant", "text": "Selam!", "sources": []}]
    ans, res, info = services.ask("hangi dosyada?", 5, "numpy", prior)
    assert info["intent"] == "notes" and "ret" in calls and ans == "cevap"


def test_meta_intent_with_history(calls, monkeypatch):
    set_an(monkeypatch, "meta")
    ans, res, info = services.ask("sen kimsin?", 5, "numpy", PRIOR)
    assert ans == "meta" and res == [] and info["intent"] == "meta" and "ret" not in calls
