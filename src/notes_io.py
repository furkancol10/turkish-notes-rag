"""Streamlit ve masaüstü arayüzünün ortak not-kaydetme yardımcıları."""
from pathlib import Path

from src import config

ALLOWED_SUFFIXES = (".md", ".txt")


def safe_note_name(name: str):
    """Dosya adını temizler (path traversal yok). Geçersizse None."""
    safe = Path(name.replace("\\", "/")).name.strip()
    if not safe or safe.startswith(".") or Path(safe).suffix.lower() not in ALLOWED_SUFFIXES:
        return None
    return safe


def save_note(name: str, data: bytes):
    """Notu NOTES_DIR'e kaydeder; kaydedilen adı döner, geçersizse None."""
    safe = safe_note_name(name)
    if safe is None:
        return None
    config.NOTES_DIR.mkdir(parents=True, exist_ok=True)
    (config.NOTES_DIR / safe).write_bytes(data)
    return safe
