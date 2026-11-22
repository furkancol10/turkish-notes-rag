import pytest

from src import config, llm


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("LLM_BACKEND", "LLM_PROVIDER", "LLM_API_KEY", "LLM_API_BASE", "LLM_API_MODEL",
              "GEMINI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(k, raising=False)


def test_backend_default_and_env(monkeypatch):
    assert llm.backend() == "ollama"
    monkeypatch.setenv("LLM_BACKEND", "API")
    assert llm.backend() == "api"
    monkeypatch.setenv("LLM_BACKEND", "bogus")
    assert llm.backend() == "ollama"


def test_backend_from_config(monkeypatch):
    monkeypatch.setattr(config, "LLM_BACKEND", "api")
    assert llm.backend() == "api"


def test_ollama_path_passes_args(monkeypatch):
    seen = {}
    monkeypatch.setattr(llm.ollama, "chat", lambda **k: seen.update(k) or {"message": {"content": "x"}})
    out = llm.chat([{"role": "user", "content": "a"}], options={"num_ctx": 1}, keep_alive="2m", think=False, format="json")
    assert out["message"]["content"] == "x"
    assert seen["model"] == config.LLM_MODEL and seen["format"] == "json" and seen["think"] is False
    seen.clear()
    llm.chat([], options={}, keep_alive="2m")
    assert "format" not in seen


def test_presets(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    s = llm.api_settings()
    assert "groq" in s["base"] and s["key"] == "k"
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert "generativelanguage" in llm.api_settings()["base"]  # gemini önce
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert "groq" in llm.api_settings()["base"]
    monkeypatch.setenv("LLM_API_MODEL", "m")
    assert llm.api_settings()["model"] == "m"


def test_api_no_key_raises():
    with pytest.raises(RuntimeError):
        llm.api_settings()


def test_payload_mapping():
    p = llm.build_payload("m", [], {"num_ctx": 4096, "temperature": 0, "num_predict": 64, "use_mmap": True}, "json")
    assert p["temperature"] == 0 and p["max_tokens"] == 64
    assert p["response_format"] == {"type": "json_object"}
    assert "num_ctx" not in p and "use_mmap" not in p
    assert "response_format" not in llm.build_payload("m", [], None, None)


def test_parse_strips_think():
    r = llm.parse_response({"choices": [{"message": {"content": "<think>x\ny</think> merhaba "}}]})
    assert r == {"message": {"role": "assistant", "content": "merhaba"}}


def test_api_chat_http_mocked(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    calls = {}

    class R:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": "cevap"}}]}

    def post(url, json, headers, timeout):
        calls.update(url=url, json=json, headers=headers)
        return R()

    monkeypatch.setattr(llm.httpx, "post", post)
    out = llm.chat([{"role": "user", "content": "s"}], options={"temperature": 0.2})
    assert out["message"]["content"] == "cevap"
    assert calls["url"].endswith("/chat/completions")
    assert calls["headers"]["Authorization"] == "Bearer k"
    assert calls["json"]["temperature"] == 0.2


def test_unload_noop_for_api(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "api")
    monkeypatch.setattr(llm.ollama, "generate", lambda **k: pytest.fail("çağrılmamalı"))
    llm.unload()
