"""Sohbet hafızası: geçmişi pencereleyip kısaltır, token bütçesine sığdırır."""
import re

_CITE = re.compile(r"\s*\[\d+(?:\s*,\s*\d+)*\]")


def approx_tokens(text: str) -> int:
    # Türkçe ≈ 3 karakter / token (temkinli)
    return (len(text) + 2) // 3


def _strip_citations(text: str) -> str:
    return re.sub(r"[ \t]{2,}", " ", _CITE.sub("", text)).strip()


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    ends = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", cut)]
    if ends and ends[-1] >= max_chars // 3:
        return cut[:ends[-1]].rstrip() + "…"
    sp = cut.rfind(" ")
    if sp > 0:
        cut = cut[:sp]
    return cut.rstrip(" ,;:-") + "…"


def window(messages: list[dict], max_turns: int = 3, max_answer_chars: int = 600) -> list[dict]:
    """Son max_turns kullanıcı/asistan turu, eskiden yeniye. Atıflar silinir, kaynaklar atılır."""
    msgs = [m for m in messages if m.get("role") in ("user", "assistant") and (m.get("text") or "").strip()]
    msgs = msgs[-2 * max_turns:]
    # Pencere asistanla başlıyorsa yetim cevabı at
    while msgs and msgs[0]["role"] == "assistant":
        msgs = msgs[1:]
    out = []
    for m in msgs:
        text = _strip_citations(m["text"])
        if m["role"] == "assistant":
            text = _truncate(text, max_answer_chars)
        out.append({"role": m["role"], "content": text})
    return out


def fit_budget(history, results, question, limit=3000, system=""):
    """Sistem+geçmiş+bağlam+soru ≤ limit token. Önce en eski geçmiş turları, sonra sondaki parçalar düşer."""
    from .chunker import chunk_label
    history = list(history or [])
    results = list(results or [])
    ctx_cost = [approx_tokens(f"[{i}] ({chunk_label(c)})\n{c.text}") + 2 for i, (c, _) in enumerate(results, 1)]

    def total():
        return (approx_tokens(system) + approx_tokens(question) + 20 + sum(ctx_cost[:len(results)])
                + sum(approx_tokens(h["content"]) + 4 for h in history))

    while history and total() > limit:
        history.pop(0)
    while len(results) > 1 and total() > limit:
        results.pop()
    return history, results
