"""ADIM 1 - YÜKLE: Not dosyalarını oku. Her not = dosya adı + metin."""
from dataclasses import dataclass
from pathlib import Path

from . import config


@dataclass
class Doc:
    source: str  # dosya adı, kaynak göstermek için kullanılır
    text: str


def load_notes(folder: Path = config.NOTES_DIR) -> list[Doc]:
    docs = []
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() in (".md", ".txt"):
            docs.append(Doc(source=path.name, text=path.read_text(encoding="utf-8")))
    return docs
