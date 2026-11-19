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


_STOP = set("""ve veya ile için gibi daha çok en bir bu şu o da de ki mi mı mu mü ne ama fakat ancak
çünkü ise olan olarak her hem tüm bazı kadar sonra önce göre ayrıca yani ya den dan ten tan
the and for with that this from are was were into your you can not but have has use used using
bunu bunun bunlar şunu onu onun ben sen biz siz var yok olur edilir edilen yapılır yapılan
sayfa adım proje aşama örnek not notlar notları kullanılır kullanılacak yapılacak etmek yapmak
sonuç kullanıcı amaç zorluk seviye süre ileri orta başlangıç temel çıktı hedef adımlar yapılacak
bilgi cevap yanıt doğal dille bölüm liste örnekler önemli gerekir sağlar ayrı farklı yeni basit
kendine örneğin çalışmalar amacı edin olduğunu önerileri oluşan ları leri ların lerin sorulardan
kitabı çözüm eklemek eklenir verilir üretim getirme birden fazla eden etme olması sohbet
uygulamalı önerisi çalışma yapılması""".split())
_INFLECTED = ("dan", "den", "tan", "ten", "nda", "nde", "ında", "inde", "ının", "inin", "ları", "leri",
              "ların", "lerin", "yla", "yle", "ına", "ine", "unu", "ünü", "ını", "ini", "ndan", "nden",
              "eden", "ılan", "ilen", "mış", "miş", "arak", "erek", "dır", "dir", "lar", "ler")
_TOK = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü][A-Za-zÇĞİÖŞÜçğıöşü0-9\-]{2,}")
_PREFIX = re.compile(r"^\s*(?:(?:Adım|Aşama|Proje|Bölüm|Kısım)\s*\d+\s*[:\-–—.]*|\d{1,2}\s*[.)]|[IVX]+\.)\s*", re.I)
_TEXT_CACHE: dict = {}


def _low(t: str) -> str:
    return t.replace("İ", "i").replace("I", "ı").lower()


def _file_text(p: Path) -> str:
    from .formats import parse
    try:
        st = p.stat()
        key = (str(p), st.st_mtime, st.st_size)
    except OSError:
        return ""
    if key not in _TEXT_CACHE:
        if len(_TEXT_CACHE) > 200:
            _TEXT_CACHE.clear()
        try:
            _TEXT_CACHE[key] = parse(p).text[:300_000]
        except Exception:
            _TEXT_CACHE[key] = ""
    return _TEXT_CACHE[key]


def _title_of(h: str) -> str | None:
    """Başlık gibi görünen metin (2-6 kelime, cümle değil, 'Adım N:' öneksiz) ya da None."""
    t = _clean(_PREFIX.sub("", re.sub(r"\s+", " ", h)))
    words = t.split()
    if not (2 <= len(words) <= 6) or len(t) > 28 or t.endswith("…") or not t[0].isalpha() \
            or t[0].islower() or words[-1].lower() in ("için", "ile", "ve"):
        return None
    if re.search(r"[.?!;,]", t) or not _ok(t):
        return None
    return t


def _concepts(texts: dict, heads: dict | None = None) -> list[tuple[float, str, Path]]:
    """TF-IDF (tekli+ikili terimler): dosyada sık, diğer dosyalarda seyrek terimler."""
    import math
    from collections import Counter
    tf, df = {}, Counter()
    surface: dict[str, Counter] = {}
    for p, txt in texts.items():
        c = Counter()
        for seg in re.split(r"[\n.,;:!?()|•\[\]\"“”—–]+", txt):
            toks = [m.group() for m in _TOK.finditer(seg)]
            low = [_low(t).strip("-") for t in toks]
            for i, w in enumerate(low):
                if w in _STOP or len(w) < 4:
                    continue
                c[w] += 1
                surface.setdefault(w, Counter())[toks[i]] += 1
                if i + 1 < len(low) and low[i + 1] not in _STOP and len(low[i + 1]) >= 4 \
                        and not toks[i][0].isupper() and not toks[i + 1][0].isupper():
                    bg = f"{w} {low[i + 1]}"
                    c[bg] += 1
                    surface.setdefault(bg, Counter())[f"{toks[i]} {toks[i + 1]}"] += 1
        tf[p] = c
        df.update(c.keys())
    n = len(texts)
    out = []
    for p, c in tf.items():
        for term, k in c.items():
            bigram = " " in term
            if k < (2 if bigram else 3):
                continue
            idf = math.log((n + 1) / (df[term] + 0.5)) + 1 if n > 1 else 1.0
            form = surface[term].most_common(1)[0][0]
            if len(form) > 24 or any(w.lower().endswith(_INFLECTED) and len(w) > 6 for w in form.split()):
                continue
            bonus = 1.6 if any(ch.isupper() for ch in form[1:]) or "-" in form else 1.0
            if heads and term in heads.get(p, ""):
                bonus *= 1.5                                  # başlıkta da geçen terim = anahtar kavram
            out.append((math.log(1 + k) * idf * (1.4 if bigram else 1.0) * bonus, form, p))
    return out


def _pick(pool, used_files, used_texts, rng, allow_repeat_file):
    pool = sorted(pool, key=lambda x: -x[0] * (0.6 + 0.8 * rng.random()))
    for sc, t, p in pool:
        if t.lower() in used_texts or (p in used_files and not allow_repeat_file):
            continue
        return t, p
    return None


def example_questions(folder: Path | None = None, n: int = 3, rng=random) -> list[str]:
    """Anahtar kavram (TF-IDF) ve bölüm başlıklarından n örnek soru; ayrı dosyalardan olmaya çalışır."""
    files = list_note_files(folder)[:40]
    texts = {p: _file_text(p) for p in files}
    texts = {p: t for p, t in texts.items() if t.strip()}
    titles, heads = [], {}
    for p in texts:
        try:
            hs = _headings(p)
        except Exception:
            hs = []
        heads[p] = _low(" ".join(hs))
        for k, h in enumerate(hs):
            t = _title_of(h)
            if t:
                titles.append((1.0 + (0.5 if k < 3 else 0), t, p))

    concepts = _concepts(texts, heads) if texts else []

    def norm(pool):
        m = max((x[0] for x in pool), default=1) or 1
        return [(s / m, t, p) for s, t, p in pool]
    concepts, titles = norm(concepts), norm(titles)
    out, used_f, used_t = [], set(), set()
    for rep in (False, True):
        for kind in "ctctct":
            if len(out) >= n:
                break
            r = _pick(concepts if kind == "c" else titles, used_f, used_t, rng, rep)
            if not r:
                continue
            t, p = r
            used_f.add(p)
            used_t.add(t.lower())
            if kind == "c":
                d = t if any(c.isupper() for c in t) or "-" in t else t[0].upper() + t[1:]
                q = f"{d} nedir?" if " " not in d and d.isupper() else \
                    rng.choice([f"{d} nedir?", f"{d} nasıl çalışır?"])
            else:
                q = f"{t} neyi anlatıyor?"
            out.append(q)
    if not out:  # başlık/kavram yok: dosya adı
        for p in files[:n]:
            t = _clean(p.stem.replace("_", " ").replace("-", " "))
            if _ok(t):
                out.append(f"{t} neyi anlatıyor?")
    return out[:n]
