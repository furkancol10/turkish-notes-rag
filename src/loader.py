"""ADIM 1 - YÜKLE: Not dosyalarını oku. Her not = göreli yol + metin."""
import os
from dataclasses import dataclass
from pathlib import Path

from . import settings

SUFFIXES = (".md", ".txt")
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__"}


@dataclass
class Doc:
    source: str  # notlar klasörüne göre göreli yol (a/b.md), kaynak göstermek için
    text: str


def list_note_files(folder: Path | None = None) -> list[Path]:
    """Klasörü özyinelemeli tarar (gizli/atlanan klasörler ve klasör symlink'leri hariç)."""
    folder = Path(folder) if folder else settings.notes_dir()
    found = []
    for root, dirs, files in os.walk(folder, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS)
        for f in sorted(files):
            if not f.startswith(".") and f.lower().endswith(SUFFIXES):
                found.append(Path(root) / f)
    return found


def rel_source(path: Path, folder: Path) -> str:
    return path.relative_to(folder).as_posix()


def newest_mtime(folder: Path | None = None) -> float | None:
    times = []
    for p in list_note_files(folder):
        try:
            times.append(p.stat().st_mtime)
        except OSError:
            pass
    return max(times) if times else None


def load_notes(folder: Path | None = None) -> list[Doc]:
    folder = Path(folder) if folder else settings.notes_dir()
    docs = []
    for path in list_note_files(folder):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue   # okunamayan dosyayı atla
        docs.append(Doc(source=rel_source(path, folder), text=text))
    return docs
