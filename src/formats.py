"""Desteklenen dosya biçimleri: TEK doğruluk kaynağı (loader, notes_io, arayüzler, mesajlar).
Yeni biçim eklemek = aşağıya bir okuyucu yazıp FORMATS'a eklemek."""
import re
from dataclasses import dataclass, field
from pathlib import Path


class SkipFile(Exception):
    """Dosya bilerek atlanır (taranmış PDF, bozuk dosya...). str(e) = sebep."""


@dataclass
class Parsed:
    text: str                                              # '# Başlık' biçimli düz metin
    pages: list[tuple[int, str]] | None = field(default=None)  # PDF: (sayfa no, metin)


# Taranmış/metinsiz PDF eşiği: sayfa başına ortalama bu kadar karakterden azsa atla
MIN_CHARS_PER_PAGE = 10
MAX_PDF_PAGES = 2000
MAX_FILE_BYTES = 100 * 1024 * 1024
NO_TEXT_MSG = "metin yok (taranmış olabilir, OCR desteklenmiyor)"


def _clean_pdf(t: str) -> str:
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)        # satır sonu tire birleştirme
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"[ \t]*\n[ \t]*", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


_PAGE_NUM = re.compile(r"\d+")


def _norm_line(l: str) -> str:
    return _PAGE_NUM.sub("#", l.strip().lower())


def strip_margins(texts: list[str]) -> list[str]:
    """Sayfaların ilk/son 2 satırında çoğu sayfada tekrarlanan satırları (üst/alt bilgi,
    'Sayfa N', sayfa numarası) atar. 3'ten az sayfada dokunmaz."""
    n = len(texts)
    if n < 3:
        return texts
    pl = [[l for l in t.split("\n") if l.strip()] for t in texts]
    cnt: dict[str, int] = {}
    for lines in pl:
        for k in {_norm_line(l) for l in lines[:2] + lines[-2:]}:
            cnt[k] = cnt.get(k, 0) + 1
    rep = {k for k, v in cnt.items() if v >= max(3, 0.8 * n)}
    out = []
    for lines in pl:
        drop = {i for i in list(range(min(2, len(lines)))) + list(range(max(0, len(lines) - 2), len(lines)))
                if _norm_line(lines[i]) in rep}
        out.append("\n".join(l for i, l in enumerate(lines) if i not in drop))
    return out


def read_text(path: Path) -> Parsed:
    try:
        return Parsed(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        raise SkipFile("UTF-8 değil")


def read_pdf(path: Path) -> Parsed:
    import pymupdf
    try:
        with pymupdf.open(path) as pdf:
            if pdf.needs_pass:
                raise SkipFile("şifreli PDF")
            if len(pdf) > MAX_PDF_PAGES:
                raise SkipFile(f"çok uzun PDF (>{MAX_PDF_PAGES} sayfa)")
            raw = [p.get_text() for p in pdf]
        pages = [(i, _clean_pdf(t)) for i, t in enumerate(strip_margins(raw), 1)]
    except SkipFile:
        raise
    except Exception as e:  # bozuk PDF
        raise SkipFile(f"okunamadı ({e.__class__.__name__})")
    total = sum(len(t) for _, t in pages)
    if total < max(20, MIN_CHARS_PER_PAGE * len(pages)):
        raise SkipFile(NO_TEXT_MSG)
    pages = [(n, t) for n, t in pages if t]
    return Parsed("\n\n".join(t for _, t in pages), pages)


def read_docx(path: Path) -> Parsed:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    try:
        d = docx.Document(str(path))
        out = []
        for el in d.element.body.iterchildren():          # belge sırasını koru
            if el.tag.endswith("}p"):
                p = Paragraph(el, d)
                t = p.text.strip()
                if not t:
                    continue
                m = re.match(r"(?:Heading|Başlık)\s*(\d)", p.style.name if p.style else "", re.I)
                if p.style is not None and p.style.name == "Title":
                    out.append(f"# {t}")
                elif m:
                    out.append(f"{'#' * min(int(m.group(1)), 6)} {t}")
                else:
                    out.append(t)
            elif el.tag.endswith("}tbl"):
                for row in Table(el, d).rows:
                    cells = []
                    for c in row.cells:
                        ct = c.text.strip()
                        if ct and ct not in cells:         # birleşik hücre tekrarını at
                            cells.append(ct)
                    if cells:
                        out.append(" | ".join(cells))
    except Exception as e:
        raise SkipFile(f"okunamadı ({e.__class__.__name__})")
    text = "\n\n".join(out)
    if not text.strip():
        raise SkipFile("metin yok")
    return Parsed(text)


def read_html(path: Path) -> Parsed:
    from bs4 import BeautifulSoup
    try:
        raw = path.read_bytes()
        soup = BeautifulSoup(raw, "html.parser")
    except Exception as e:
        raise SkipFile(f"okunamadı ({e.__class__.__name__})")
    for t in soup(["script", "style", "nav", "footer", "noscript", "template", "head"]):
        t.decompose()
    for h in soup.find_all(["h1", "h2", "h3"]):
        h.replace_with(soup.new_string(f"\n\n{'#' * int(h.name[1])} {h.get_text(' ', strip=True)}\n\n"))
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for t in soup.find_all(["p", "div", "li", "tr", "section", "article", "h4", "h5", "h6",
                            "table", "ul", "ol", "pre", "blockquote"]):
        t.insert_before("\n\n")
        t.insert_after("\n\n")
    text = soup.get_text()
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise SkipFile("metin yok")
    return Parsed(text)


# uzantı -> (etiket, okuyucu)
FORMATS = {
    ".md": ("MD", read_text),
    ".txt": ("TXT", read_text),
    ".pdf": ("PDF", read_pdf),
    ".docx": ("DOCX", read_docx),
    ".html": ("HTML", read_html),
    ".htm": ("HTML", read_html),
}

SUFFIXES = tuple(FORMATS)
UPLOAD_TYPES = [s.lstrip(".") for s in SUFFIXES]          # Streamlit uploader
LABELS = list(dict.fromkeys(lbl for lbl, _ in FORMATS.values()))
LABEL_TEXT = ", ".join(LABELS)                              # "MD, TXT, PDF, DOCX, HTML"
SUFFIX_TEXT = "/".join(s for s in SUFFIXES)                 # ".md/.txt/..."
DIALOG_FILTER = f"Notlar ({' '.join('*' + s for s in SUFFIXES)})"   # Qt dosya penceresi
NO_NOTES_MSG = f"Bu klasörde not yok (desteklenen biçimler: {LABEL_TEXT})."


def is_supported(name: str) -> bool:
    return name.lower().endswith(SUFFIXES)


def parse(path: Path) -> Parsed:
    if path.stat().st_size > MAX_FILE_BYTES:
        raise SkipFile("dosya çok büyük (>100 MB)")
    return FORMATS[path.suffix.lower()][1](path)
