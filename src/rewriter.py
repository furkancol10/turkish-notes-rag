"""Takip sorusunu (\"peki gemini ne önermiş?\") geçmişe bakarak bağımsız arama sorgusuna çevirir."""
import re

import ollama

from . import config
from .router import normalize

SYSTEM = (
    "Sohbet geçmişine bakarak son kullanıcı mesajını, geçmişe ihtiyaç duymadan anlaşılan "
    "tek bir Türkçe arama sorusuna dönüştür. Zamirleri ve eksik özneleri açık yaz. "
    "Soruyu CEVAPLAMA. Sadece yeniden yazılmış soruyu çıkar, başka hiçbir şey yazma. "
    "Soru, kullanıcının notlarındaki bilgiyi arayan üçüncü şahıs sorusu olsun (\"-siniz\" ile bitmesin). "
    "Örnek: geçmişte \"ChatGPT hangi projeleri önermiş?\" varsa ve son mesaj \"peki gemini?\" ise "
    "çıktı: Gemini hangi projeleri önermiş?"
)

_REF_WORDS = {
    "bu", "bunu", "bunun", "bunlar", "bunlari", "bundan", "buna", "su", "sunu", "sunun",
    "o", "onu", "onun", "onlar", "onlari", "ondan", "ona", "orada", "burada", "surada",
    "peki", "ya", "aynisi", "ayni", "digeri", "diger", "digerleri", "hangisi", "hangileri",
    "ilki", "ikincisi", "ucuncusu", "sonuncusu", "ilkini", "ikincisini", "sonuncuyu",
    "ilk", "son", "oyleyse", "yani", "bide", "ayrica", "baska", "daha", "de", "da",
    "ilkinin", "ikincinin", "sonuncunun", "onlarin", "bunlarin", "ilkine", "peki",
}
_ORDINAL = re.compile(r"\b\d+ (madde|maddeyi|maddesi|nolu|numarali|sira)|\b(madde|numara) \d+")
_MIN_WORDS = 4


def needs_rewrite(question: str, history: list[dict]) -> bool:
    """Ucuz sezgi: soru kendi başına anlaşılıyorsa LLM'e gitme."""
    if not history:
        return False
    q = normalize(question)
    if not q:
        return False
    words = q.split()
    if len(words) < _MIN_WORDS:
        return True
    if _ORDINAL.search(q):
        return True
    # Cümle başı "peki/ya/ve" ya da referans sözcüğü
    if any(w in _REF_WORDS for w in words):
        return True
    return False


_PREFIX = re.compile(r"^\s*(yeniden yazılmış soru|yeniden yazılmış|bağımsız soru|arama sorusu|sorgu|soru|cevap)\s*[:\-]\s*",
                     re.IGNORECASE)


def _clean(text: str) -> str:
    text = (text or "").strip().splitlines()[0].strip() if (text or "").strip() else ""
    q = "\"'“”‘’`«» "
    return _PREFIX.sub("", text.strip(q)).strip(q)


def _valid(out: str, question: str) -> bool:
    if not out or len(out) > max(3 * len(question), 150):
        return False
    # Cevap verme belirtisi: soru değil ve soru kalıbı yok
    if "?" not in out:
        tail = normalize(out).split()[-1:] or [""]
        if not re.fullmatch(r"(mi|mu|mı|mü|midir|nedir|nelerdir|neler|ne|nasil|kim|kac|hangisi|hangileri|var)", tail[0]) \
                and not re.search(r"\b(ne|nasil|hangi|kim|kac|neden|nerede|nelerdir|nedir|mi|mu)\b", normalize(out)):
            return False
    return True


def condense(question: str, history: list[dict]) -> str:
    if not history or not needs_rewrite(question, history):
        return question
    try:
        convo = "\n".join(
            f"{'Kullanıcı' if m['role'] == 'user' else 'Asistan'}: {m['content']}" for m in history)
        resp = ollama.chat(
            model=config.LLM_MODEL,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": f"Geçmiş:\n{convo}\n\nSon mesaj: {question}\n\nBağımsız soru:"}],
            options={**config.LLM_OPTIONS, "temperature": 0, "num_predict": 64},
            keep_alive=config.LLM_KEEP_ALIVE, think=False,
        )
        out = _clean(resp["message"]["content"])
    except Exception:
        return question
    return out if _valid(out, question) else question
