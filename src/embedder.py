"""ADIM 3 - EMBED: Metni sayı vektörüne çevir. Anlamca yakın metinler yakın vektör olur.

Toplu işler (indeksleme, eval) GPU'da (fp16), tek soru CPU'da çalışır; GPU yoksa/hata verirse CPU'ya düşer.
"""
import logging

import numpy as np

from . import config

log = logging.getLogger(__name__)
_models: dict[tuple[str, str], object] = {}
_cuda_broken = False  # bir CUDA hatasından sonra bu oturumda GPU denenmez


def _cuda_available() -> bool:
    if _cuda_broken:
        return False
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _disable_cuda(err: Exception) -> None:
    global _cuda_broken
    if not _cuda_broken:
        log.warning("CUDA hatası (%s); embedding CPU'ya düşüyor.", err)
    _cuda_broken = True
    release_gpu()


def resolve_device(setting: str) -> str:
    if setting == "auto":
        return "cuda" if _cuda_available() else "cpu"
    if setting.startswith("cuda") and not _cuda_available():
        return "cpu"
    return setting


def resolve_index_device() -> str:
    return resolve_device(config.EMBED_DEVICE_INDEX)


def get_model(device: str = "cpu", name: str | None = None):
    """Modeli cihaz başına bir kez yükler (önbellek)."""
    from sentence_transformers import SentenceTransformer
    key = (name or config.EMBED_MODEL, device)
    if key not in _models:
        m = SentenceTransformer(key[0], device=device)
        if device.startswith("cuda") and config.EMBED_INDEX_DTYPE == "float16":
            m = m.half()
        _models[key] = m
    return _models[key]


def release_gpu() -> None:
    """GPU modellerini bırakır, VRAM'i işletim sistemine geri verir."""
    for key in [k for k in _models if k[1].startswith("cuda")]:
        del _models[key]
    try:
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def unload_llm() -> None:
    """Ollama'dan LLM'i boşalt (indekslemede tepe VRAM'i düşük tutar); hatalar yok sayılır."""
    try:
        import ollama
        ollama.generate(model=config.LLM_MODEL, prompt="", keep_alive=0)
    except Exception:
        pass


def _encode(texts: list[str], prefix: str, model: str, device: str) -> np.ndarray:
    vecs = get_model(device, model).encode(
        [prefix + t for t in texts], batch_size=config.EMBED_BATCH_SIZE if device != "cpu" else 8,
        normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype=np.float32)


def _run(texts, prefix, model, device):
    if device.startswith("cuda"):
        try:
            return _encode(texts, prefix, model, device)
        except Exception as e:  # OOM dahil her CUDA hatası
            _disable_cuda(e)
            device = "cpu"
    return _encode(texts, prefix, model, device)


def embed_passages(texts: list[str], model: str = config.EMBED_MODEL) -> np.ndarray:
    return _run(texts, config.PASSAGE_PREFIX.get(model, ""), model, resolve_index_device())


def embed_query(text: str, model: str = config.EMBED_MODEL) -> np.ndarray:
    return _run([text], config.QUERY_PREFIX.get(model, ""), model, resolve_device(config.EMBED_DEVICE_QUERY))[0]
