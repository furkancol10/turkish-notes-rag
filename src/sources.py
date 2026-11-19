"""Kaynak sorusu ("hangi dosyada/sayfada?") için LLM'siz, deterministik cevap."""
import re

_CITE = re.compile(r"\[(\s*\d+(?:\s*(?:[,;\-–]\s*\d+)*)\s*)\]")


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
