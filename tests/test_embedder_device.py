"""Embedding cihaz seçimi (CPU-only CI'da çalışır; torch.cuda taklit edilir)."""
import numpy as np
import pytest

from src import config, embedder


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(embedder, "_cuda_broken", False)
    monkeypatch.setattr(embedder, "_models", {})


def _cuda(monkeypatch, ok):
    monkeypatch.setattr(embedder, "_cuda_available", lambda: ok)


def test_auto_picks_cuda_when_available(monkeypatch):
    _cuda(monkeypatch, True)
    assert embedder.resolve_device("auto") == "cuda"


def test_auto_falls_back_to_cpu(monkeypatch):
    _cuda(monkeypatch, False)
    assert embedder.resolve_device("auto") == "cpu"
    assert embedder.resolve_device("cuda") == "cpu"
    assert embedder.resolve_device("cpu") == "cpu"


def test_query_stays_on_cpu_passages_on_gpu(monkeypatch):
    _cuda(monkeypatch, True)
    seen = []
    monkeypatch.setattr(embedder, "_encode", lambda t, p, m, d: seen.append(d) or np.zeros((len(t), 2), np.float32))
    embedder.embed_query("soru")
    embedder.embed_passages(["a", "b"])
    assert seen == [config.EMBED_DEVICE_QUERY, "cuda"] and config.EMBED_DEVICE_QUERY == "cpu"


def test_cuda_error_falls_back_to_cpu_once(monkeypatch):
    _cuda(monkeypatch, True)
    monkeypatch.setattr(embedder, "release_gpu", lambda: None)
    calls = []

    def enc(t, p, m, d):
        calls.append(d)
        if d == "cuda":
            raise RuntimeError("CUDA out of memory")
        return np.ones((len(t), 2), np.float32)
    monkeypatch.setattr(embedder, "_encode", enc)
    monkeypatch.setattr(embedder, "_cuda_available", lambda: not embedder._cuda_broken)
    out = embedder.embed_passages(["a"])
    assert out.shape == (1, 2) and calls == ["cuda", "cpu"]
    embedder.embed_passages(["a"])
    assert calls == ["cuda", "cpu", "cpu"]  # bir daha GPU denenmez


def test_model_cached_per_device(monkeypatch):
    created = []

    class Fake:
        def __init__(self, name, device, **kw): created.append(device)
    import sentence_transformers
    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", Fake)
    embedder.get_model("cpu"); embedder.get_model("cpu"); embedder.get_model("cuda")
    assert created == ["cpu", "cuda"]


def test_unload_llm_ignores_errors(monkeypatch):
    import ollama
    monkeypatch.setattr(ollama, "generate", lambda **k: (_ for _ in ()).throw(ConnectionError()))
    embedder.unload_llm()
