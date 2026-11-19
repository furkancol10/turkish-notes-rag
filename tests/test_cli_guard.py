from types import SimpleNamespace

from src import cli, config
from src.entities import guard_note


def test_guard_note_blocks_missing_entity():
    chunks = [SimpleNamespace(text="Ali'nin doğum günü mayısta")]
    assert "Zeynep" in guard_note("Zeynep'in doğum günü ne zaman?", chunks)
    assert guard_note("Ali'nin doğum günü ne zaman?", chunks) is None


def test_cmd_ask_skips_llm_when_entity_missing(monkeypatch, capsys):
    c = SimpleNamespace(id="a#0", text="Ali'nin doğum günü mayısta")
    monkeypatch.setattr(cli, "_apply_dir", lambda a: None)
    monkeypatch.setattr(cli, "route", lambda q: "notes")
    monkeypatch.setattr(cli, "retrieve", lambda q, backend=None: [(c, 0.9)])
    monkeypatch.setattr(cli, "chunk_label", lambda c: "x")
    monkeypatch.setattr(cli, "_threshold", lambda a: None)
    monkeypatch.setattr(cli, "_catalog", lambda b: None)
    monkeypatch.setattr(config, "ENTITY_GUARD_ENABLED", True)
    def boom(*a, **k):
        raise AssertionError("LLM called")
    monkeypatch.setattr(cli, "answer", boom)
    cli.cmd_ask(SimpleNamespace(question="Zeynep'in doğum günü ne zaman?", backend="chroma"))
    assert "Zeynep" in capsys.readouterr().out
