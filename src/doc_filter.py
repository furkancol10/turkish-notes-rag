"""Belge düzeyinde filtre: soru belirli bir belgeyi anıyorsa ("chatgpt ne önermiş") aramayı o belgeyle sınırla.
Ayrıca birebir/yakın kopya parçaları (aynı içerik .pdf + .html) tekilleştir."""
import hashlib
import re
from pathlib import PurePosixPath

from .router import normalize

MAX_DOCS = 3          # bundan çok belge eşleşirse belirsiz say -> filtre yok
MAX_DF = 3            # bir takma ad bundan çok belgede geçiyorsa ayırt edici değil, at
MIN_LEN = 3
JACCARD = 0.9

# Tek başına hiçbir şey ayırt etmeyen sözcükler (normalize edilmiş biçimde)
GENERIC = {
    "rag", "not", "notlar", "notlari", "note", "notes", "ders", "dersi", "rapor", "raporu", "proje", "projesi",
    "projeler", "toplanti", "kitap", "tarif", "teknik", "dosya", "belge", "doc", "docs", "pdf", "html", "md",
    "txt", "final", "yeni", "kopya", "copy", "v", "ozet", "tasarim", "genel", "fikir", "kisisel", "data", "test",
}
# Yerleşik takma adlar: sözcük -> kanonik ad (hem soruda hem belge adında uygulanır)
BUILTIN = {
    "chatgpt": "gpt", "gpt": "gpt", "openai": "gpt",
    "gemini": "gemini", "bard": "gemini",
    "deepseek": "deepseek", "qwen": "qwen",
    "claude": "claude", "anthropic": "claude",
    "llama": "llama", "mistral": "mistral", "copilot": "copilot",
}


def _canon(tok: str) -> str:
    return BUILTIN.get(tok, tok)


def _split_name(stem: str) -> list[str]:
    s = re.sub(r"([a-zçğıöşü])([A-ZÇĞİÖŞÜ])", r"\1 \2", stem)      # camelCase
    s = re.sub(r"([A-Za-zÇĞİÖŞÜçğıöşü])(\d)|(\d)([A-Za-zÇĞİÖŞÜçğıöşü])", lambda m: " ".join(g for g in m.groups() if g), s)
    return [_canon(t) for t in normalize(re.sub(r"[_\-.\s]+", " ", s)).split() if not t.isdigit()]


def _tokens(text: str) -> list[str]:
    return [_canon(t) for t in normalize(text).split()]


def build_catalog(sources: list[str], titles: dict[str, str] | None = None) -> dict[str, set[tuple]]:
    """source -> takma ad kümesi; her takma ad bir sözcük demeti (tek sözcük ya da ardışık çok sözcük)."""
    titles = titles or {}
    raw: dict[str, set[tuple]] = {}
    for src in sources:
        al: set[tuple] = set()
        toks = _split_name(PurePosixPath(src).stem)
        for t in toks:
            if t not in GENERIC and len(t) >= MIN_LEN:
                al.add((t,))
        for n in range(2, len(toks) + 1):
            for i in range(len(toks) - n + 1):
                al.add(tuple(toks[i:i + n]))
        title = _tokens(titles.get(src, ""))
        if 0 < len(title) <= 6:
            if len(title) > 1:
                al.add(tuple(title))
        raw[src] = al
    df: dict[tuple, int] = {}
    for al in raw.values():
        for a in al:
            df[a] = df.get(a, 0) + 1
    return {s: {a for a in al if df[a] <= MAX_DF} for s, al in raw.items()}


def _tok_match(qt: str, alias_tok: str) -> bool:
    if qt == alias_tok:
        return True
    # Türkçe ek toleransı: "novanın", "chatgpt'nin" (kısa takma adlarda yalnız tam eşleşme)
    return len(alias_tok) >= 4 and qt.startswith(alias_tok) and len(qt) - len(alias_tok) <= 4


def _matches(qtoks: list[str], alias: tuple) -> bool:
    n = len(alias)
    return any(all(_tok_match(qtoks[i + j], alias[j]) for j in range(n)) for i in range(len(qtoks) - n + 1))


def detect(question: str, catalog: dict[str, set[tuple]]) -> list[str] | None:
    qtoks = _tokens(question)
    hit = [s for s, al in catalog.items() if any(_matches(qtoks, a) for a in al)]
    if not hit or len(hit) > MAX_DOCS:
        return None
    return sorted(hit)


def detect_many(questions: list[str], catalog) -> list[str] | None:
    found: set[str] = set()
    for q in questions:
        d = detect(q, catalog) if q else None
        if d:
            found.update(d)
    return sorted(found) if found and len(found) <= MAX_DOCS else None


# --- Tekilleştirme ---
def _norm_text(t: str) -> str:
    return " ".join(re.sub(r"\W+", " ", t.lower()).split())


def dedupe(results: list, k: int | None = None) -> list:
    """Aynı/yakın içerikli parçalardan birini tut (pdf tercih: sayfa no); sıra korunur."""
    kept: list = []
    keys: list[tuple[str, set]] = []
    for ch, sc in results:
        nt = _norm_text(ch.text)
        h = hashlib.sha1(nt.encode()).hexdigest()
        ws = set(nt.split())
        dup = None
        for i, (h2, ws2) in enumerate(keys):
            if h == h2 or (ws and ws2 and len(ws & ws2) / len(ws | ws2) >= JACCARD):
                dup = i
                break
        if dup is None:
            kept.append((ch, sc))
            keys.append((h, ws))
        elif ch.source.lower().endswith(".pdf") and not kept[dup][0].source.lower().endswith(".pdf"):
            kept[dup] = (ch, kept[dup][1])
    return kept[:k] if k else kept
