"""Boş sohbet ekranı için örnek sorular: geçerli not klasöründeki başlıklardan, LLM'siz, anında."""
import random
import re
from pathlib import Path

from .loader import list_note_files

MAX_LEN = 50
_JUNK = re.compile(r"ÖRNEK NOT|^[\W\d_]*$|^(sayfa|page)\s*\d+$", re.I)
_GENERIC = {"rapor", "raporu", "sayfa", "içindekiler", "giriş", "özet", "sonuç", "kaynakça",
            "özet", "ekler", "önsöz", "başlangıç", "page", "contents", "introduction",
            "conclusion", "summary", "abstract", "references", "tablo", "şekil"}


def _clean(t: str) -> str:
    t = re.sub(r"\(?\s*ÖRNEK NOT\s*\)?", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" #*-_:.\t")
    if len(t) > MAX_LEN:
        t = t[:MAX_LEN].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
    return t


def _ok(t: str) -> bool:
    if len(t) < 4 or _JUNK.search(t) or sum(c.isalpha() for c in t) < 3:
        return False
    words = t.split()
    return not (len(words) == 1 and (words[0].lower().strip("….") in _GENERIC or len(t) < 6)) \
        and t.lower().strip("….") not in _GENERIC


_NUMBERED = re.compile(r"^(\d{1,2}[.)]|Proje \d+\s*[:\-—]|Adım \d+\s*:|Bölüm \d+)\s*\S")


def _pdf_headings(pdf, max_pages: int = 30) -> list[str]:
    """Yazı boyutu gövdeden büyük satırlar + numaralı başlıklar; sayfalar arası tekrarlayanlar
    (üst/alt bilgi) ve tek kelimelik/genel başlıklar hariç."""
    import collections
    body = collections.Counter()
    cand = []                                   # (sayfa, boyut, metin)
    for pno, page in enumerate(pdf):
        if pno >= max_pages:
            break
        for b in page.get_text("dict")["blocks"]:
            prev = None
            for ln in b.get("lines", []):
                txt = "".join(sp["text"] for sp in ln["spans"]).strip()
                if not txt:
                    continue
                size = round(max(sp["size"] for sp in ln["spans"]) * 2) / 2
                body[size] += len(txt)
                if prev and prev[1] == size and not _NUMBERED.match(txt) and len(prev[2]) < 70:
                    cand[-1] = (pno, size, prev[2] + " " + txt)     # kırık başlık satırını birleştir
                    prev = cand[-1]
                else:
                    cand.append((pno, size, txt))
                    prev = cand[-1]
    if not body:
        return []
    base = body.most_common(1)[0][0]
    seen = collections.Counter(t.lower() for _, _, t in cand)
    out = []
    for pno, size, t in cand:
        if seen[t.lower()] > 1 or len(t) > 90:
            continue
        if t[0].islower():
            continue                              # kırık satır parçası
        if size >= base + 2 or _NUMBERED.match(t):
            out.append(t)
    return out


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
            return _pdf_headings(pdf)
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
