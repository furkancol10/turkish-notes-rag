"""Streamlit ve masaüstü arayüzünün ortak not-kaydetme yardımcıları."""
from pathlib import Path

from src import settings
from src.formats import SUFFIXES

ALLOWED_SUFFIXES = SUFFIXES


def safe_note_name(name: str):
    """Dosya adını temizler (path traversal yok). Geçersizse None."""
    safe = Path(name.replace("\\", "/")).name.strip()
    if not safe or safe.startswith(".") or Path(safe).suffix.lower() not in ALLOWED_SUFFIXES:
        return None
    return safe


def save_note(name: str, data: bytes):
    """Notu not klasörüne kaydeder; kaydedilen adı döner, geçersizse None."""
    safe = safe_note_name(name)
    if safe is None:
        return None
    folder = settings.notes_dir()
    folder.mkdir(parents=True, exist_ok=True)
    # Aynı adlı not varsa üzerine yazma: "ad (2).md"
    target, n = folder / safe, 2
    while target.exists():
        target = folder / f"{Path(safe).stem} ({n}){Path(safe).suffix}"
        n += 1
    target.write_bytes(data)
    return target.name
