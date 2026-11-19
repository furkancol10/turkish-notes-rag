"""ADIM 1 - YÜKLE: Not dosyalarını oku. Her not = göreli yol + metin."""
import os
import warnings
from dataclasses import dataclass
from pathlib import Path

from . import settings
from .formats import SUFFIXES, SkipFile, is_supported, parse
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__"}


@dataclass
class Doc:
    source: str  # notlar klasörüne göre göreli yol (a/b.md), kaynak göstermek için
    text: str
    pages: list[tuple[int, str]] | None = None  # PDF: (sayfa no, metin); sayfa bilgisi chunk'a taşınır


def list_note_files(folder: Path | None = None) -> list[Path]:
    """Klasörü özyinelemeli tarar (gizli/atlanan klasörler ve klasör symlink'leri hariç)."""
    folder = Path(folder) if folder else settings.notes_dir()
    found = []
    for root, dirs, files in os.walk(folder, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS)
        for f in sorted(files):
            if not f.startswith(".") and is_supported(f):
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


@dataclass
class LoadReport:
    docs: list[Doc]
    skipped: list[tuple[str, str]]   # (kaynak, sebep): okunamayan / metinsiz dosyalar
    unsupported: int = 0             # desteklenmeyen uzantılı dosya sayısı

    @property
    def n_skipped(self) -> int:
        return len(self.skipped) + self.unsupported


def count_unsupported(folder: Path) -> int:
    n = 0
    for root, dirs, files in os.walk(folder, followlinks=False):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
        n += sum(1 for f in files if not f.startswith(".") and not is_supported(f))
    return n


def load_report(folder: Path | None = None) -> LoadReport:
    folder = Path(folder) if folder else settings.notes_dir()
    docs, skipped = [], []
    for path in list_note_files(folder):
        src = rel_source(path, folder)
        try:
            parsed = parse(path)
        except SkipFile as e:
            warnings.warn(f"Not atlandı ({src}): {e}")
            skipped.append((src, str(e)))
            continue
        except Exception as e:  # okunamayan dosya asla indekslemeyi düşürmesin
            warnings.warn(f"Not atlandı ({src}): {e.__class__.__name__}")
            skipped.append((src, e.__class__.__name__))
            continue
        docs.append(Doc(source=src, text=parsed.text, pages=parsed.pages))
    return LoadReport(docs, skipped, count_unsupported(folder))


def load_notes(folder: Path | None = None) -> list[Doc]:
    return load_report(folder).docs
