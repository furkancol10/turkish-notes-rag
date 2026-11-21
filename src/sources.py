"""Kaynak sorusu ("hangi dosyada/sayfada?") için LLM'siz, deterministik cevap."""
import re

from . import settings

_CITE = re.compile(r"\[(\s*\d+(?:\s*(?:[,;\-–]\s*\d+)*)\s*)\]")
_CITE_ONE = r"\[[ \t]*\d+(?:[ \t]*(?:[,;\-–][ \t]*\d+)*)[ \t]*\](?!\()"
_CITE_CHAIN = rf"{_CITE_ONE}(?:(?:[ \t]*,[ \t]*|[ \t]*){_CITE_ONE})*"
_STRIP_RE = re.compile(
    rf"(?P<fence>^[ \t]*(?P<f_bt>`{{3,}})[^\n]*(?:\n.*?(?:^[ \t]*(?P=f_bt)`*[ \t]*\r?$|\Z)|\Z))"
    rf"|(?P<inline>(?<!`)(?P<i_bt>`+)(?!`)(?:(?!\n\n).)+?(?<!`)(?P=i_bt)(?!`))"
    rf"|(?:(?P<bol>^)(?P<indent>[ \t]*)|(?P<pre>[ \t]+))(?P<cite>{_CITE_CHAIN})(?P<post>[ \t]*)",
    re.MULTILINE | re.DOTALL,
)
_NO_SPACE_BEFORE = set(".,;:!?)]}»”’")
_CLOSING_MARK = set("*_~\"'")


def strip_citations(text: str) -> str:
    """Metindeki [1], [1, 3], [2-4], [1][2] atıf işaretlerini ve önündeki boşluğu siler.

    Markdown bağlantıları, görev kutuları, sayısal olmayan köşeli parantezler, dizi indeksleri
    (a[1]) ve satır içi / çitli kod blokları korunur.
    """
    def _repl(m: re.Match) -> str:
        if m.group("fence") is not None or m.group("inline") is not None:
            return m.group(0)
        end = m.end()
        after = "" if end == len(text) else text[end]
        at_eol = not after or after in ("\n", "\r")
        if m.group("bol") is not None:
            return "" if at_eol else m.group("indent")
        if at_eol:
            return ""
        if after in _NO_SPACE_BEFORE or (not m.group("post") and after in _CLOSING_MARK):
            return ""
        return " "

    return _STRIP_RE.sub(_repl, text)


def display_text(text: str) -> str:
    """Atıf ayarı açıksa metni aynen, kapalıysa atıfsız hâlini döndürür."""
    return text if settings.get_show_citations() else strip_citations(text)


def cited_indices(answer_text: str, n_sources: int) -> list[int]:
    """Cevaptaki [1], [1, 3], [2-4] atıflarının 1-tabanlı, sıralı, tekil, aralıktaki listesi."""
    out: list[int] = []
    for m in _CITE.finditer(answer_text or ""):
        body = m.group(1)
        nums: list[int] = []
        for part in re.split(r"[,;]", body):
            rng = re.split(r"[\-–]", part.strip())
            if len(rng) == 2 and rng[0].strip() and rng[1].strip():
                a, b = int(rng[0]), int(rng[1])
                nums += range(a, b + 1) if a <= b and b - a < 100 else [a, b]
            elif rng[0].strip():
                nums.append(int(rng[0]))
        for n in nums:
            if 1 <= n <= n_sources and n not in out:
                out.append(n)
    return out


def _group(sources: list[dict], idxs: list[int]) -> list[tuple[str, list[int], list[str]]]:
    groups: dict[str, tuple[list[int], list[str]]] = {}
    for i in idxs:
        s = sources[i - 1]
        pages, heads = groups.setdefault(str(s.get("source", "")), ([], []))
        p = s.get("page")
        if p and p not in pages:
            pages.append(p)
        h = s.get("heading")
        if h and h not in heads:
            heads.append(h)
    return [(f, sorted(p), h) for f, (p, h) in groups.items()]


def answer_sources(prev_answer_text: str, prev_sources: list[dict], question: str = "") -> str:
    sources = list(prev_sources or [])
    if not sources:
        return "Önceki cevap notlardan bir kaynağa dayanmıyordu."
    idxs = cited_indices(prev_answer_text, len(sources))
    if idxs:
        head = "Önceki cevap şu kaynaklara dayanıyor:"
    else:
        idxs = list(range(1, len(sources) + 1))
        head = "Cevapta açık atıf yoktu; getirilen kaynaklar:"
    page_q = "sayfa" in (question or "").lower()
    lines = []
    for f, pages, heads in _group(sources, idxs):
        line = f"- **{f}**"
        if pages:
            line += f" — {'sayfa' if page_q else 's.'} " + ", ".join(map(str, pages))
        if heads:
            line += " (" + "; ".join(heads[:3]) + ")"
        lines.append(line)
    return head + "\n" + "\n".join(lines)
