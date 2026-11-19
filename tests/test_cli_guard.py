from types import SimpleNamespace

from src import cli, config, qa
from src.entities import guard_note


def test_guard_note_blocks_missing_entity():
    chunks = [SimpleNamespace(text="Ali'nin doğum günü mayısta")]
    assert "Zeynep" in guard_note("Zeynep'in doğum günü ne zaman?", chunks)
    assert guard_note("Ali'nin doğum günü ne zaman?", chunks) is None


def test_cmd_ask_skips_llm_when_entity_missing(monkeypatch, capsys):
    c = SimpleNamespace(id="a#0", text="Ali'nin doğum günü mayısta")
    monkeypatch.setattr(cli, "_apply_dir", lambda a: None)
    monkeypatch.setattr(qa, "analyze", lambda q, h: {"intent": "notes", "query": q})
    monkeypatch.setattr(qa, "retrieve", lambda q, k=None, backend=None: [(c, 0.9)])
    monkeypatch.setattr(cli, "chunk_label", lambda c: "x")
    monkeypatch.setattr(cli, "_threshold", lambda a: None)
    monkeypatch.setattr(qa, "_doc_catalog", lambda b: None)
    monkeypatch.setattr(qa, "load_embed_model", lambda: None)
    monkeypatch.setattr(qa, "index_status", lambda: object())
    monkeypatch.setattr(config, "ENTITY_GUARD_ENABLED", True)
    def boom(*a, **k):
        raise AssertionError("LLM called")
    monkeypatch.setattr(qa, "answer", boom)
    cli.cmd_ask(SimpleNamespace(question="Zeynep'in doğum günü ne zaman?", backend="chroma"))
    assert "Zeynep" in capsys.readouterr().out
