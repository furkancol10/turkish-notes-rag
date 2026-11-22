"""Tek LLM sohbet girişi: yerel Ollama (varsayılan) veya OpenAI uyumlu bulut API (Colab'da GPU yoksa).

Dönüş her iki backend'de de Ollama biçimindedir: {"message": {"content": "..."}}.
Backend: env LLM_BACKEND ("ollama" | "api"), yoksa config.LLM_BACKEND.
API ayarları (env): LLM_API_KEY / GEMINI_API_KEY / GROQ_API_KEY, LLM_API_BASE, LLM_API_MODEL, LLM_PROVIDER.
"""
import os
import re

import httpx
import ollama

from . import config

PRESETS = {
    "gemini": {"base": "https://generativelanguage.googleapis.com/v1beta/openai",
               "model": "gemini-2.5-flash", "key_env": "GEMINI_API_KEY"},
    "groq": {"base": "https://api.groq.com/openai/v1",
             "model": "llama-3.3-70b-versatile", "key_env": "GROQ_API_KEY"},
}
TIMEOUT = 120.0


def backend() -> str:
    b = (os.environ.get("LLM_BACKEND") or getattr(config, "LLM_BACKEND", "ollama") or "ollama").strip().lower()
    return b if b in ("ollama", "api") else "ollama"


def api_settings() -> dict:
    """Env'den {base, model, key}; sağlayıcı LLM_PROVIDER'dan ya da hangi anahtar varsa ondan seçilir."""
    env = os.environ.get
    provider = (env("LLM_PROVIDER") or "").lower()
    if provider not in PRESETS:
        provider = next((p for p, v in PRESETS.items() if env(v["key_env"])), "")
    preset = PRESETS.get(provider, {})
    key = env("LLM_API_KEY") or (env(preset["key_env"]) if preset else None)
    base = env("LLM_API_BASE") or preset.get("base")
    model = env("LLM_API_MODEL") or preset.get("model")
    if not (key and base and model):
        raise RuntimeError("API backend için anahtar gerekli: GEMINI_API_KEY, GROQ_API_KEY "
                           "ya da LLM_API_KEY + LLM_API_BASE + LLM_API_MODEL")
    return {"base": base.rstrip("/"), "model": model, "key": key}


def build_payload(model: str, messages: list[dict], options: dict | None, format: str | None) -> dict:
    """Ollama seçeneklerini OpenAI alanlarına çevir (num_ctx, use_mmap vb. yok sayılır)."""
    options = options or {}
    p = {"model": model, "messages": messages}
    if "temperature" in options:
        p["temperature"] = options["temperature"]
    if "num_predict" in options:
        p["max_tokens"] = options["num_predict"]
    if "top_p" in options:
        p["top_p"] = options["top_p"]
    if format == "json":
        p["response_format"] = {"type": "json_object"}
    return p


def parse_response(data: dict) -> dict:
    content = data["choices"][0]["message"].get("content") or ""
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
    return {"message": {"role": "assistant", "content": content}}


def _api_chat(messages, options, format) -> dict:
    s = api_settings()
    r = httpx.post(f"{s['base']}/chat/completions", json=build_payload(s["model"], messages, options, format),
                   headers={"Authorization": f"Bearer {s['key']}"}, timeout=TIMEOUT)
    r.raise_for_status()
    return parse_response(r.json())


def chat(messages: list[dict], *, options: dict | None = None, keep_alive=None,
         think: bool | None = False, format: str | None = None) -> dict:
    if backend() == "api":
        return _api_chat(messages, options, format)
    kw = {"format": format} if format else {}
    return ollama.chat(model=config.LLM_MODEL, messages=messages, options=options,
                       keep_alive=keep_alive, think=think, **kw)


def unload() -> None:
    """Yalnız Ollama'da modeli VRAM'den boşalt; API backend'de işlem yok."""
    if backend() != "ollama":
        return
    ollama.generate(model=config.LLM_MODEL, prompt="", keep_alive=0)
