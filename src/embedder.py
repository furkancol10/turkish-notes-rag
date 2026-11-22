"""ADIM 3 - EMBED: Metni sayı vektörüne çevir. Anlamca yakın metinler yakın vektör olur.

İndeksleme ve tek soru aynı GPU modelini (fp16, tek önbellekli örnek) paylaşır; GPU yoksa/OOM olursa CPU'ya düşer (bir kez loglanır).
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
        kw = {}
        if device.startswith("cuda") and config.EMBED_INDEX_DTYPE == "float16":
            kw["model_kwargs"] = {"torch_dtype": "float16"}  # doğrudan fp16 yükle (fp32 tepe VRAM'i yok)
        m = SentenceTransformer(key[0], device=device, **kw)
        _models[key] = m
    return _models[key]


def warmup_query_model():
    """Soru modelini önceden yükler (GPU, olmazsa CPU'ya düşer)."""
    device = resolve_device(config.EMBED_DEVICE_QUERY)
    if device.startswith("cuda"):
        try:
            return get_model(device)
        except Exception as e:  # yükleme sırasında OOM vb.
            _disable_cuda(e)
    return get_model("cpu")


def release_index_model() -> None:
    """İndeksleme sonrası GPU modelini, soru modeli olarak kullanılmıyorsa bırakır."""
    if not resolve_device(config.EMBED_DEVICE_QUERY).startswith("cuda"):
        release_gpu()


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
        from . import llm
        llm.unload()
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
