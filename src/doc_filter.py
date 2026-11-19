"""Belge düzeyinde filtre: soru belirli bir belgeyi anıyorsa ("chatgpt ne önermiş") aramayı o belgeyle sınırla.
Ayrıca birebir/yakın kopya parçaları (aynı içerik .pdf + .html) tekilleştir."""
import hashlib
import re
from pathlib import PurePosixPath

from .router import normalize

MAX_DOCS = 3          # bundan çok belge eşleşirse belirsiz say -> filtre yok
MAX_DF = 3            # bir takma ad bundan çok belgede geçiyorsa ayırt edici değil, at
MIN_LEN = 3
JACCARD = 0.8          # sıralı 3'lü kelime gruplarında (shingle) benzerlik eşiği

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


# Bilinen Türkçe ekler (ASCII'ye katlanmış); takma ad + ek eşleşmesi yalnız bunlarla kabul edilir
_TR_SUFFIXES = {
    "n", "m", "in", "nin", "un", "nun", "i", "yi", "u", "yu", "a", "ya", "e", "ye",
    "da", "de", "ta", "te", "dan", "den", "tan", "ten", "la", "le", "yla", "yle",
    "lar", "ler", "lari", "leri", "larin", "lerin", "daki", "deki", "nda", "nde",
    "ndan", "nden", "na", "ne", "si", "su", "sin", "sun", "im", "um", "imiz",
    "mde", "mda", "mden", "mdan", "imde", "imda", "imden", "imdan", "imi", "ini", "mi", "mu", "ni", "nu", "umu", "unu", "ki", "ndaki", "ndeki",
}


def _canon(tok: str) -> str:
    if tok in BUILTIN:
        return BUILTIN[tok]
    for k, v in BUILTIN.items():      # "chatgptye" (kesme işaretsiz ek)
        if len(k) >= 4 and tok.startswith(k) and tok[len(k):] in _TR_SUFFIXES:
            return v
    return tok


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
        title_raw = titles.get(src, "")
        name_slot = _name_slot(title_raw) if title_raw else None
        for i, t in enumerate(toks):
            if t in GENERIC or len(t) < MIN_LEN:
                continue
            if t in BUILTIN.values() or _single_is_specific(i, t, name_slot):
                al.add((t,))
        for n in range(2, len(toks) + 1):
            for i in range(len(toks) - n + 1):
                al.add(tuple(toks[i:i + n]))
        title = _tokens(titles.get(src, ""))
        for i in range(len(title) - 1):      # sayı içeren ikili ("21 ders"): adın parçası
            if any(w.isdigit() for w in title[i:i + 2]):
                al.add(tuple(title[i:i + 2]))
        if 0 < len(title) <= 6:
            if len(title) > 1:
                al.add(tuple(title))
        raw[src] = al
    df: dict[tuple, int] = {}
    for al in raw.values():
        for a in al:
            df[a] = df.get(a, 0) + 1
    return {s: {a for a in al if df[a] <= MAX_DF} for s, al in raw.items()}


def _name_slot(title: str) -> tuple[set[str], str | None]:
    """Başlıktaki ad kısmı. "Film Notu: Inception" -> ({inception}, None): iki nokta sonrası ad sayılır.
    İki nokta yoksa ({tüm başlık sözcükleri}, ilk sözcük): ilk sözcük konu/kategori sayılır, ad olamaz
    ("Veri Yapıları Ders Notları"); "Proje Nova Toplantısı" -> nova ad olabilir."""
    t = title.strip()
    if ":" in t:
        return set(_tokens(t.rsplit(":", 1)[1])), None
    toks = _tokens(t)
    return set(toks), (toks[0] if len(toks) > 1 else None)


def _single_is_specific(idx: int, tok: str, slot) -> bool:
    """Tek sözcük yalnız özel adsa (başlıktaki ad kısmı / kategori önekinden sonraki ad) belgeyi işaret eder.
    Sıradan isimler (_is_common) ve konu sözcükleri asla; başlık yoksa kategori önekinden sonraki sözcük."""
    if _is_common(tok):
        return False
    if slot is None:
        return idx > 0
    names, first = slot
    return tok in names and tok != first


def _tok_match(qt: str, alias_tok: str) -> bool:
    if qt == alias_tok:
        return True
    # Türkçe ek toleransı: "novanın", "chatgpt'nin" (kısa takma adlarda yalnız tam eşleşme)
    return len(alias_tok) >= 4 and qt.startswith(alias_tok) and qt[len(alias_tok):] in _TR_SUFFIXES


def _is_common(tok: str) -> bool:
    return tok in COMMON or any(tok.endswith(s) and tok[: -len(s)] in COMMON for s in _TR_SUFFIXES)


def _matches(qtoks: list[str], alias: tuple) -> bool:
    n = len(alias)
    return any(all(_tok_match(qtoks[i + j], alias[j]) for j in range(n)) for i in range(len(qtoks) - n + 1))


# Dosya adı gövdesinden gelen, tek başına ayırt edici olmayan sıradan isimler (normalize edilmiş)
COMMON = {
    "butce", "tarif", "toplanti", "ders", "kitap", "film", "seyahat", "spor", "saglik", "uyku", "fikir", "blog",
    "yazi", "yazilari", "haftalik", "aylik", "gunluk", "program", "kosu", "liste", "listeler", "kelime", "kelimeler",
    "giris", "plan", "yemek", "corba", "komut", "komutlari", "teknik", "not", "notlar", "ozet", "rapor", "proje",
}


def _n_docs(sources) -> int:
    """Aynı gövdeli dosyalar (deepseekRag.pdf + deepseekRag.html) tek belge sayılır."""
    return len({str(PurePosixPath(s).with_suffix("")).lower() for s in sources})


def _typed_file(question: str, src: str) -> bool:
    """Kullanıcı dosya adını/gövdesini aynen yazdı ("kisisel_butce.md", "gptRag")."""
    q = question.lower()
    p = PurePosixPath(src)
    return p.name.lower() in q or (len(p.stem) >= 4 and p.stem.lower() in q)


def detect(question: str, catalog: dict[str, set[tuple]]) -> list[str] | None:
    """Yalnız belirli göndermeler filtreler: yerleşik takma ad, çok sözcüklü ad, özel ad, yazılmış dosya adı.
    Sıradan isimler (bütçe, film, veri...) tek başına asla filtrelemez."""
    qtoks = _tokens(question)
    hit = [s for s, al in catalog.items() if _typed_file(question, s) or any(_matches(qtoks, a) for a in al)]
    if not hit or _n_docs(hit) > MAX_DOCS:
        return None
    return sorted(hit)


def detect_many(questions: list[str], catalog) -> list[str] | None:
    found: set[str] = set()
    for q in questions:
        d = detect(q, catalog) if q else None
        if d:
            found.update(d)
    return sorted(found) if found and _n_docs(found) <= MAX_DOCS else None


# --- Tekilleştirme ---
def _norm_text(t: str) -> str:
    return " ".join(re.sub(r"\W+", " ", t.lower()).split())


def _shingles(nt: str, n: int = 3) -> set:
    w = nt.split()
    return {tuple(w[i:i + n]) for i in range(max(1, len(w) - n + 1))} if w else set()


def dedupe(results: list, k: int | None = None) -> list:
    """Aynı/yakın içerikli parçalardan birini tut (pdf tercih: sayfa no); sıra korunur."""
    kept: list = []
    keys: list[tuple[str, set]] = []
    for ch, sc in results:
        nt = _norm_text(ch.text)
        h = hashlib.sha1(nt.encode()).hexdigest()
        ws = _shingles(nt)
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
