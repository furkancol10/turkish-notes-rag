"""Soru-cevap hattı (src/qa.py) karakterizasyon testleri: services.ask, cli ask/chat ve qa.ask aynı davranışı verir.
LLM ve arama taklit edilir; stub'lar hangi modülde varsa oraya (cli/services/qa) yamanır."""
import builtins
from types import SimpleNamespace

import pytest

from desktop import services
from src import cli, config

try:
    from src import qa
except ImportError:   # refactor öncesi
    qa = SimpleNamespace()

CH = SimpleNamespace(id="a.md#0", source="a.md", heading="H", page=0, text="Ali'nin bütçesi 450 bin TL")
SRC = [{"source": "nova.md", "heading": "B", "page": None, "score": 0.9, "text": "Bütçe 450 bin TL"}]
PRIOR = [{"role": "user", "text": "Nova bütçesi?", "sources": []},
         {"role": "assistant", "text": "450 bin TL [1].", "sources": SRC, "intent": "notes"}]


@pytest.fixture
def env(monkeypatch):
    st = {"intent": "notes", "score": 0.8, "ans": []}

    def patch(name, val):
        for mod in (cli, services, qa):
            if hasattr(mod, name):
                monkeypatch.setattr(mod, name, val)

    def analyze(q, h=None):
        return {"intent": st["intent"], "query": st.get("query") or q}
    patch("analyze", analyze)
    monkeypatch.setattr("src.rewriter.analyze", analyze)
    patch("route", lambda q: "meta" if st["intent"] == "meta" else "notes")
    patch("answer_meta", lambda q: "meta")
    patch("answer_followup", lambda q, h, s: "takip")
    monkeypatch.setattr("src.generator.answer_followup", lambda q, h, s: "takip")

    def ans(q, results, history=None):
        st["ans"].append(q)
        return "cevap"
    patch("answer", ans)
    patch("retrieve", lambda q, k=None, backend=None: [(CH, st["score"])])
    patch("load_embed_model", lambda: None)
    patch("index_status", lambda: object())
    patch("_doc_catalog", lambda b: None)
    patch("_catalog", lambda b: None)
    monkeypatch.setattr(config, "ENTITY_GUARD_ENABLED", False)
    st["patch"] = patch
    return st


def _svc(**kw):
    return services.ask("Bütçe ne?", 5, "numpy", [], **kw)


def test_services_notes(env):
    a, r, info = _svc(threshold=0.5, threshold_enabled=True)
    assert (a, info) == ("cevap", {"intent": "notes", "query": None}) and r == [(CH, 0.8)]


@pytest.mark.parametrize("intent,out", [("meta", "meta")])
def test_services_meta(env, intent, out):
    env["intent"] = intent
    assert services.ask("x", 5, "numpy", [])[0] == out


def test_services_followup_and_sources(env):
    env["intent"] = "followup"
    a, r, info = services.ask("peki?", 5, "numpy", PRIOR)
    assert a == "takip" and r[0][0].source == "nova.md" and info["intent"] == "followup"
    env["intent"] = "sources"
    a, r, info = services.ask("kaynak?", 5, "numpy", PRIOR)
    assert info["intent"] == "sources" and r[0][0].source == "nova.md" and not env["ans"]


def test_services_threshold(env):
    env["score"] = 0.3
    a, r, info = _svc(threshold=0.5, threshold_enabled=True)
    assert a == config_not_in_notes() and info["below_threshold"] is True
    assert info["top_score"] == 0.3 and info["threshold"] == 0.5 and info["note"] and not env["ans"]
    assert _svc(threshold=0.5, threshold_enabled=False)[0] == "cevap"


def config_not_in_notes():
    from src.formats import NOT_IN_NOTES
    return NOT_IN_NOTES


def test_services_entity_guard(env, monkeypatch):
    monkeypatch.setattr(config, "ENTITY_GUARD_ENABLED", True)
    a, r, info = services.ask("Zeynep'in bütçesi ne?", 5, "numpy", [], threshold=0.1, threshold_enabled=True)
    assert a == config_not_in_notes() and "Zeynep" in info["note"] and info["entity_missing"]
    assert not env["ans"]
    assert services.ask("Ali'nin bütçesi ne?", 5, "numpy", [], threshold=0.1, threshold_enabled=True)[0] == "cevap"


def test_services_errors(env):
    env["patch"]("index_status", lambda: None)
    with pytest.raises(services.AskError) as e:
        _svc(threshold=0.1, threshold_enabled=True)
    assert e.value.kind == "index"


def _args(**kw):
    d = dict(question="Bütçe ne?", backend="numpy", threshold=None, no_threshold=True, notes_dir=None)
    d.update(kw)
    return SimpleNamespace(**d)


@pytest.fixture(autouse=True)
def _nodir(monkeypatch):
    monkeypatch.setattr(cli, "_apply_dir", lambda a: None)


def test_cli_ask_paths(env, capsys, monkeypatch):
    cli.cmd_ask(_args())
    out = capsys.readouterr().out
    assert "Cevap:\ncevap" in out and "a.md#0" in out
    env["intent"] = "meta"
    cli.cmd_ask(_args())
    assert "Cevap:\nmeta" in capsys.readouterr().out
    env["intent"], env["score"] = "notes", 0.3
    cli.cmd_ask(_args(no_threshold=False, threshold=0.5))
    out = capsys.readouterr().out
    assert config_not_in_notes() in out and "cevap\n" not in out
    monkeypatch.setattr(config, "ENTITY_GUARD_ENABLED", True)
    env["score"] = 0.9
    cli.cmd_ask(_args(question="Zeynep'in bütçesi ne?"))
    out = capsys.readouterr().out
    assert config_not_in_notes() in out and "Zeynep" in out


def _chat(monkeypatch, qs, **kw):
    it = iter(qs)
    monkeypatch.setattr(builtins, "input", lambda p="": next(it, ""))
    cli.cmd_chat(_args(**kw))


def test_cli_chat_turns(env, capsys, monkeypatch):
    _chat(monkeypatch, ["Bütçe ne?"])
    assert "Cevap:\ncevap" in capsys.readouterr().out
    env["score"] = 0.3
    _chat(monkeypatch, ["Bütçe ne?"], no_threshold=False, threshold=0.5)
    assert config_not_in_notes() in capsys.readouterr().out
    monkeypatch.setattr(config, "ENTITY_GUARD_ENABLED", True)
    env["score"] = 0.9
    _chat(monkeypatch, ["Zeynep'in bütçesi ne?"])
    assert "Zeynep" in capsys.readouterr().out
    env["ans"].clear()
    env["intent"] = "meta"
    _chat(monkeypatch, ["merhaba"])
    assert "Cevap:\nmeta" in capsys.readouterr().out


def test_cli_chat_followup_uses_previous_sources(env, capsys, monkeypatch):
    seen = []
    env["patch"]("answer_followup", lambda q, h, s: seen.append(s) or "takip")
    monkeypatch.setattr("src.generator.answer_followup", lambda q, h, s: seen.append(s) or "takip")
    it = iter(["Bütçe ne?", "peki?"])

    def inp(p=""):
        v = next(it, "")
        if v == "peki?":
            env["intent"] = "followup"
        return v
    monkeypatch.setattr(builtins, "input", inp)
    cli.cmd_chat(_args())
    out = capsys.readouterr().out
    assert "Cevap:\ntakip" in out and seen and seen[0][0]["source"] == "a.md"
