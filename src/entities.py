"""Varlık-varlığı koruması: soruda geçen özel ad (kişi/proje/ürün/kod) hiçbir getirilen parçada geçmiyorsa
LLM çağrılmaz. Belge adı/başlığında geçen varlıkları doc_filter zaten ele alır; bu modül yalnız İÇERİK'te
geçen varlıkları kapsar. Sezgisel: yalnız özel ad adayları (büyük harf, tırnak, kod) denetlenir."""
import re

from .doc_filter import GENERIC, _matches, _tokens
from .router import normalize

_W = r"[^\W\d_]+(?:['’][^\W\d_]+)?"           # sözcük (+ kesme işaretli ek: Ayşe'nin)
_WORD_RE = re.compile(_W)
_QUOTE_RE = re.compile(r"[\"“”«]([^\"“”«»]{2,60})[\"“”»]")
_CODE_RE = re.compile(r"\b(?=[A-Za-z0-9\-]*\d)(?=[A-Za-z0-9\-]*[A-Za-z])[A-Za-z0-9][A-Za-z0-9\-]{1,}\b")

# Büyük harfle yazılsa da özel ad olmayan sözcükler (normalize edilmiş) + belge türü sözcükleri
STOP = {
    "ne", "nedir", "neden", "nasil", "nerede", "nereye", "nereden", "kim", "kimin", "kimler", "kimdir", "hangi",
    "kac", "kaci", "kadar", "ne", "zaman", "ben", "sen", "biz", "siz", "bu", "su", "o", "bana", "bize", "benim",
    "bir", "ve", "ile", "icin", "ama", "veya", "ya", "da", "de", "mi", "mu", "var", "yok", "evet", "hayir",
    "ocak", "subat", "mart", "nisan", "mayis", "haziran", "temmuz", "agustos", "eylul", "ekim", "kasim", "aralik",
    "pazartesi", "sali", "carsamba", "persembe", "cuma", "cumartesi", "pazar", "turkiye", "turkce", "ingilizce",
    "notlarimda", "notlarda", "notlarima", "notum", "notlarim",
    "bey", "hanim", "hoca", "hocam", "abi", "abla", "dr", "prof", "doc",
    "hafta", "haftasi", "gecen", "bugun", "dun", "yarin", "sabah", "aksam", "gece",
    "ay", "yil", "sene", "toplanti", "toplantida", "toplantisi",
    "i", "me", "my", "you", "we", "it", "the", "what", "who", "when", "where", "why", "how", "did", "do",
} | set(GENERIC) | {"projesi", "proje", "dersi", "ders", "kitabi", "kitap", "yazar", "yazari", "plani", "tarifi"}


_DIGIT_SPLIT = re.compile(r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)")


def _fold_words(s: str) -> list[str]:
    return [t for t in _DIGIT_SPLIT.sub(" ", normalize(s)).split() if t]


def _is_stop(w: str) -> bool:
    t = _fold_words(w)
    return not t or all(x in STOP for x in t)


def _dedupe(seq):
    seen, out = set(), []
    for x in seq:
        k = " ".join(_fold_words(x))
        if k and k not in seen:
            seen.add(k)
            out.append(x)
    return out


def extract(query: str, catalog: dict | None = None) -> list[str]:
    """Sorudan özel ad adayları: tırnaklı terimler, alfasayısal kodlar, büyük harfli sözcük/öbekler
    (cümle başındaki büyük harf sayılmaz; kesme işaretli cümle başı sözcük sayılır). catalog verilirse
    belge adıyla eşleşenler (doc_filter'ın işi) atılır."""
    q = query or ""
    out: list[str] = [m.group(1).strip() for m in _QUOTE_RE.finditer(q)]
    q_noquote = _QUOTE_RE.sub(" ", q)
    out += [m.group(0) for m in _CODE_RE.finditer(q_noquote)]
    # cümle başı konumları: metnin başı ve . ! ? sonrası
    starts = {0}
    for m in re.finditer(r"[.!?]\s+", q_noquote):
        starts.add(m.end())
    span: list[str] = []

    def flush():
        while span and _is_stop(span[0]):
            span.pop(0)
        while span and _is_stop(span[-1]):
            span.pop()
        if span:
            out.append(" ".join(span))
        span.clear()

    pos = 0
    for m in _WORD_RE.finditer(q_noquote):
        w = m.group(0)
        gap = q_noquote[pos:m.start()]
        if span and re.search(r"[^\s]", gap):          # noktalama araya girdi: öbek biter
            flush()
        pos = m.end()
        first = w[0].isupper()
        sent_start = m.start() in starts
        if first and (not sent_start or "'" in w or "’" in w):
            stem = re.split(r"['’]", w)[0]
            if _is_stop(stem) and not span:
                continue
            span.append(stem)
        else:
            flush()
    flush()
    res = []
    for e in _dedupe(out):
        if len(e.strip()) < 2:
            continue
        if catalog and _in_catalog(e, catalog):
            continue
        res.append(e)
    return res


def _in_catalog(entity: str, catalog: dict) -> bool:
    qt = _tokens(entity)
    return any(_matches(qt, a) for al in catalog.values() for a in al if len(a) <= len(qt))


def _tok_in(e: str, t: str) -> bool:
    if e == t:
        return True
    if len(e) < 4 or len(t) < 4:
        return False
    p = 0
    while p < min(len(e), len(t)) and e[p] == t[p]:
        p += 1
    return p >= max(4, min(len(e), len(t)) - 2)


def present(entity: str, chunk_texts) -> bool:
    """Varlığın tüm sözcükleri (Türkçe ek toleransıyla) herhangi bir parçada geçiyor mu?"""
    et = _fold_words(entity)
    if not et:
        return True
    for txt in chunk_texts:
        ct = set(_fold_words(txt or ""))
        if all(any(_tok_in(e, t) for t in ct) for e in et):
            return True
    return False


def missing(query: str, chunk_texts, catalog: dict | None = None) -> list[str]:
    """Soruda özel ad varsa ve HİÇBİRİ parçalarda yoksa adların listesi, aksi halde []."""
    ents = extract(query, catalog)
    texts = list(chunk_texts)
    if ents and not any(present(e, texts) for e in ents):
        return ents
    return []


def guard_note(query: str, chunks, catalog: dict | None = None) -> str | None:
    """Paylaşılan koruma (cli için): eksik varlık varsa kullanıcıya gösterilecek not, yoksa None."""
    miss = missing(query, [c.text for c in chunks], catalog)
    if not miss:
        return None
    return "Notlarda " + ", ".join(f"“{m}”" for m in miss) + " geçen bir bölüm bulunamadı."
