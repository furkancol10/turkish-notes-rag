"""Boş sohbet ekranı için örnek sorular: geçerli not klasöründeki başlıklardan, LLM'siz, anında."""
import random
import re
from pathlib import Path

from .loader import list_note_files

MAX_LEN = 50
_JUNK = re.compile(r"ÖRNEK NOT|^[\W\d_]*$|^(sayfa|page)\s*\d+$", re.I)


def _clean(t: str) -> str:
    t = re.sub(r"\(?\s*ÖRNEK NOT\s*\)?", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" #*-_:.\t")
    if len(t) > MAX_LEN:
        t = t[:MAX_LEN].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
    return t


def _ok(t: str) -> bool:
    return len(t) >= 4 and not _JUNK.search(t) and sum(c.isalpha() for c in t) >= 3


def _headings(path: Path) -> list[str]:
    ext = path.suffix.lower()
    if ext in (".md", ".txt"):
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        h = [l.lstrip("#") for l in lines if re.match(r"#{1,6}\s", l)]
        return h or [l for l in lines if l.strip()][:1]
    if ext == ".docx":
        import docx
        d = docx.Document(str(path))
        return [p.text for p in d.paragraphs
                if p.style is not None and re.match(r"(Heading|Başlık|Title)", p.style.name)]
    if ext in (".html", ".htm"):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        return [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
    if ext == ".pdf":
        import pymupdf
        with pymupdf.open(path) as pdf:
            if len(pdf):
                return [l for l in pdf[0].get_text().splitlines() if _ok(_clean(l))][:3]
    return []


def example_questions(folder: Path | None = None, n: int = 3, rng=random) -> list[str]:
    """Farklı dosyalardan en çok n örnek soru; uygun başlık yoksa dosya adı kullanılır."""
    files = list_note_files(folder)
    rng.shuffle(files)
    out = []
    for p in files[:12]:
        try:
            cands = [c for c in (_clean(h) for h in _headings(p)) if _ok(c)]
        except Exception:
            cands = []
        title = rng.choice(cands) if cands else _clean(p.stem.replace("_", " ").replace("-", " "))
        if _ok(title) and title not in out:
            out.append(title)
        if len(out) == n:
            break
    return [f"«{t}» hakkında notlarımda ne var?" for t in out]
