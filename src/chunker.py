"""ADIM 2 - PARÇALA: Uzun notları küçük parçalara (chunk) böl.
Neden? Embedding modeli kısa metinde daha isabetli çalışır ve LLM'e sadece ilgili parça gider."""
import re
from dataclasses import dataclass

from . import config
from .loader import Doc

HEADING = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


@dataclass
class Chunk:
    id: str       # "dosya.md#3"
    source: str   # hangi nottan geldi
    heading: str  # en yakın üst başlık (metadata)
    text: str
    page: int = 0  # PDF sayfa no (0 = sayfa yok)


def _heading_at(text: str, pos: int) -> str:
    """pos konumundan önceki son başlığı bul."""
    last = ""
    for m in HEADING.finditer(text):
        if m.start() > pos:
            break
        last = m.group(1).strip()
    return last


def chunk_fixed(doc: Doc, size: int, overlap: int) -> list[Chunk]:
    """Sabit boyut + örtüşme: her parça `size` karakter, komşu parça `overlap` kadar paylaşır
    (cümle ortada kesilirse bilgi kaybolmasın diye)."""
    chunks, start = [], 0
    while start < len(doc.text):
        piece = doc.text[start:start + size].strip()
        if piece:
            chunks.append(Chunk(f"{doc.source}#{len(chunks)}", doc.source,
                                _heading_at(doc.text, start), piece))
        if start + size >= len(doc.text):
            break
        start += size - overlap
    return chunks


def chunk_by_heading(doc: Doc, size: int = config.CHUNK_SIZE,
                     overlap: int = config.CHUNK_OVERLAP) -> list[Chunk]:
    """Başlık bazlı: her '#' başlığı yeni parça başlatır (notun doğal yapısını korur).
    `size`'dan uzun bölümler sabit boyut + örtüşme ile bölünür."""
    parts = re.split(r"(?m)^(?=#{1,6}\s)", doc.text)
    chunks = []
    for part in parts:
        if not part.strip():
            continue
        m = HEADING.match(part)
        heading = m.group(1).strip() if m else ""
        pieces = ([part.strip()] if len(part.strip()) <= size else
                  [c.text for c in chunk_fixed(Doc(doc.source, part), size, overlap)])
        for text in pieces:
            chunks.append(Chunk(f"{doc.source}#{len(chunks)}", doc.source, heading, text))
    return chunks


def chunk_pages(doc: Doc, size: int, overlap: int) -> list[Chunk]:
    """PDF: her sayfa kendi içinde parçalanır, böylece parça sayfa numarasını kaybetmez."""
    chunks = []
    for page, text in doc.pages:
        for c in chunk_fixed(Doc(doc.source, text), size, overlap):
            chunks.append(Chunk(f"{doc.source}#{len(chunks)}", doc.source, "", c.text, page))
    return chunks


def chunk_label(c: Chunk) -> str:
    """Kaynak gösterimi: 'dosya.pdf, s. 3 / Başlık' (sayfa/başlık yoksa o kısım düşer)."""
    loc = f"{c.source}, s. {c.page}" if c.page else c.source
    return f"{loc} / {c.heading}" if c.heading or not c.page else loc


def chunk_docs(docs: list[Doc], strategy: str = config.CHUNK_STRATEGY,
               size: int = config.CHUNK_SIZE, overlap: int = config.CHUNK_OVERLAP) -> list[Chunk]:
    out = []
    for d in docs:
        if d.pages:
            out += chunk_pages(d, size, overlap)
        else:
            out += chunk_by_heading(d, size, overlap) if strategy == "heading" else chunk_fixed(d, size, overlap)
    return out
