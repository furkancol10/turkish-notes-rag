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


def test_sources_never_shows_rewritten_query(calls, monkeypatch):
    set_an(monkeypatch, "sources", "Nova bütçesi hangi dosyada geçiyor?")
    _, _, info = services.ask("hangi dosyada?", 5, "numpy", PRIOR2)
    assert info["query"] is None


def test_sources_out_of_range_citation_lists_all(calls, monkeypatch):
    set_an(monkeypatch, "sources")
    prior = [PRIOR[0], {"role": "assistant", "text": "450 bin [7].", "sources": SRC2}]
    _, res, _ = services.ask("hangi dosyada?", 5, "numpy", prior)
    assert len(res) == 2


SRC_LIST = {"role": "assistant", "text": "nova.md dosyasında.", "intent": "sources", "sources": SRC[:1]}
NOTES_MSG = {"role": "assistant", "text": "450 bin TL [1].", "intent": "notes", "sources": SRC}
OTHER = [{"source": "baska.md", "heading": "", "page": None, "score": 0.5, "text": "x"}]


def test_followup_after_sources_uses_earlier_notes_answer(calls, monkeypatch):
    set_an(monkeypatch, "followup")
    prior = [{"role": "user", "text": "q", "sources": []}, NOTES_MSG,
             {"role": "user", "text": "hangi dosya?", "sources": []},
             {**SRC_LIST, "sources": OTHER}]
    ans, results, info = services.ask("kısaca anlat", 4, "numpy", prior)
    assert calls["fu"][2] == SRC and info["intent"] == "followup"


def test_sources_after_meta_uses_notes_answer(calls, monkeypatch):
    set_an(monkeypatch, "sources")
    prior = [NOTES_MSG, {"role": "assistant", "text": "Ben asistanım.", "intent": "meta", "sources": []}]
    ans, results, info = services.ask("hangi dosyada?", 4, "numpy", prior)
    assert info["intent"] == "sources" and results[0][0].source == "nova.md"


def test_legacy_messages_without_intent(calls, monkeypatch):
    set_an(monkeypatch, "followup")
    legacy = {"role": "assistant", "text": "450", "sources": SRC}
    services.ask("kısaca", 4, "numpy", [legacy])
    assert calls["fu"][2] == SRC


def test_last_notes_message_skips_sourceless():
    from src import history
    assert history.last_notes_message([{"role": "assistant", "text": "a", "intent": "notes", "sources": []}]) is None
    assert history.last_notes_message([NOTES_MSG, SRC_LIST]) is NOTES_MSG


def test_intent_saved_and_restored(tmp_path, monkeypatch):
    from src import history
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    c = history.new_chat("n")
    c["messages"] = [{"role": "user", "text": "q", "sources": []}, NOTES_MSG]
    history.save_chat(c)
    got = history.load_chat(c["id"])
    assert got["messages"][1]["intent"] == "notes"
    assert conversation.window(got["messages"])[1] == {"role": "assistant", "content": "450 bin TL."}


def test_notes_prompt_has_entity_rule():
    from src.generator import SYSTEM
    assert "AYNI" in SYSTEM and "farklı" in SYSTEM and "notlarda yok" in SYSTEM


# ---- skor eşiği ----
def low(calls, monkeypatch, score):
    monkeypatch.setattr(services, "retrieve", lambda q, k, backend: [(CH, score)])


def test_below_threshold_skips_llm(calls, monkeypatch):
    low(calls, monkeypatch, 0.38)
    ans, res, info = services.ask("soru", 5, "numpy", [], 0.45, True)
    assert ans == "Bu bilgi notlarda yok." and "ans" not in calls and res == [(CH, 0.38)]
    assert info["below_threshold"] is True and info["top_score"] == 0.38 and info["intent"] == "notes"
    assert info["note"] == "En yakın eşleşme: a.md (skor 0.38) — eşik 0.45"


def test_above_threshold_and_disabled(calls, monkeypatch):
    ans, res, info = services.ask("soru", 5, "numpy", [], 0.45, True)
    assert ans == "cevap" and "below_threshold" not in info
    low(calls, monkeypatch, 0.1)
    calls.pop("ans", None)
    ans, _, info = services.ask("soru", 5, "numpy", [], 0.45, False)
    assert ans == "cevap" and "ans" in calls and "below_threshold" not in info


def test_threshold_from_settings(calls, monkeypatch, tmp_path):
    from src import settings
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    settings.set_score_threshold(0.9)
    assert services.ask("soru", 5, "numpy", [])[2].get("below_threshold")
    settings.set_threshold_enabled(False)
    assert services.ask("soru", 5, "numpy", [])[0] == "cevap"


def test_meta_unaffected(calls, monkeypatch):
    low(calls, monkeypatch, 0.0)
    assert services.ask("merhaba", 5, "numpy", [], 0.9, True)[0] == "meta"


def test_below_threshold_message_not_followup_base():
    from src import history
    m = {"role": "assistant", "text": "x", "intent": "notes", "below_threshold": True, "sources": SRC}
    assert history.last_notes_message([m]) is None
