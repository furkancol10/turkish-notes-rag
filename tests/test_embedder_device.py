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


def test_query_and_index_both_use_cuda(monkeypatch):
    monkeypatch.setattr(config, "EMBED_DEVICE_QUERY", "auto")  # GPU sorgu modu (varsayılan cpu)
    _cuda(monkeypatch, True)
    seen = []
    monkeypatch.setattr(embedder, "_encode", lambda t, p, m, d: seen.append(d) or np.zeros((len(t), 2), np.float32))
    embedder.embed_query("soru")
    embedder.embed_passages(["a", "b"])
    assert seen == ["cuda", "cuda"]


def test_query_cpu_when_no_cuda(monkeypatch):
    _cuda(monkeypatch, False)
    assert embedder.resolve_device(config.EMBED_DEVICE_QUERY) == "cpu"


def _fake_st(monkeypatch, created, fail_cuda=False):
    class Fake:
        def __init__(self, name, device, **kw):
            if fail_cuda and device == "cuda":
                raise RuntimeError("CUDA out of memory")
            created.append(device)
    import sentence_transformers
    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", Fake)


def test_single_shared_model_not_freed_after_indexing(monkeypatch):
    monkeypatch.setattr(config, "EMBED_DEVICE_QUERY", "auto")  # GPU sorgu modu (varsayılan cpu)
    _cuda(monkeypatch, True)
    created = []
    _fake_st(monkeypatch, created)
    m1 = embedder.warmup_query_model()
    embedder.release_index_model()  # indeksleme sonrası
    assert embedder.get_model(embedder.resolve_index_device()) is m1
    assert embedder.get_model(embedder.resolve_device(config.EMBED_DEVICE_QUERY)) is m1
    assert created == ["cuda"]


def test_index_model_freed_when_query_on_cpu(monkeypatch):
    _cuda(monkeypatch, True)
    monkeypatch.setattr(config, "EMBED_DEVICE_QUERY", "cpu")
    _fake_st(monkeypatch, [])
    embedder.get_model("cuda")
    embedder.release_index_model()
    assert not any(k[1].startswith("cuda") for k in embedder._models)


def test_warmup_falls_back_on_load_oom(monkeypatch):
    monkeypatch.setattr(config, "EMBED_DEVICE_QUERY", "auto")  # GPU sorgu modu (varsayılan cpu)
    _cuda(monkeypatch, True)
    monkeypatch.setattr(embedder, "_cuda_available", lambda: not embedder._cuda_broken)
    created = []
    _fake_st(monkeypatch, created, fail_cuda=True)
    embedder.warmup_query_model()
    assert created == ["cpu"] and embedder._cuda_broken


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
