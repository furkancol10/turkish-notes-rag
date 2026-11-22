"""Takip sorusunu (\"peki gemini ne önermiş?\") geçmişe bakarak bağımsız arama sorgusuna çevirir."""
import json
import re


from . import config, llm
from .router import has_new_content, is_sources, normalize, route

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
        resp = llm.chat(
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": f"Geçmiş:\n{convo}\n\nSon mesaj: {question}\n\nBağımsız soru:"}],
            options={**config.LLM_OPTIONS, "temperature": 0, "num_predict": 64},
            keep_alive=config.LLM_KEEP_ALIVE, think=False,
        )
        out = _clean(resp["message"]["content"])
    except Exception:
        return question
    return out if _valid(out, question) else question


# --- Tek çağrıda niyet + bağımsız sorgu ---
_INTENTS = {"followup", "sources", "notes", "meta"}
INTENT_SYSTEM = (
    "Sohbet geçmişine bakarak kullanıcının SON mesajının niyetini sınıflandır ve bağımsız bir "
    "Türkçe arama sorusu yaz. Sadece JSON çıkar: {\"intent\": \"...\", \"query\": \"...\"}\n"
    "intent değerleri:\n"
    "- followup: SADECE önceki asistan cevabının kendisi hakkında ve yeni bilgi gerektirmeden o cevaptan "
    "yanıtlanır (doğru mu, emin misin, kısalt, özetle, madde madde yaz, ilkini açıkla, neden böyle).\n"
    "- sources: önceki cevabın HANGİ dosya/sayfa/nottan geldiğini soruyor.\n"
    "- notes: notlarda YENİ bilgi aramak gerekiyor. Yeni bir konu/ayrıntı/kişi/sayı soran her mesaj notes'tur; "
    "kısa ve eksiltili olsa da (peki kira?, ya teslim tarihi?, onun bütçesi ne?, kimler katıldı?). "
    "Mesajda önceki cevapta olmayan bir konu sözcüğü varsa notes. \"Başka hangi raporda/notta geçiyor?\" da notes.\n"
    "- meta: asistanın kendisi hakkında (kimsin, hangi modelsin, teşekkür).\n"
    "Şüphede notes seç.\n"
    "query: geçmişe ihtiyaç duymayan tek soru. Zamirleri ve eksik özneyi geçmişten aç; kullanıcının kendi "
    "anahtar sözcüklerini ve soru kalıbını (\"hangi dosyada\", \"başka hangi notta\") AYNEN koru, konuyu değiştirme. "
    "Cevaplama. followup/meta için query = son mesaj.\n"
    "Örnekler (geçmiş: Re-ranking anlatıldı):\n"
    "\"hangi dosyada bundan bahsetmiş\" -> {\"intent\":\"sources\",\"query\":\"Re-ranking hangi dosyada geçiyor?\"}\n"
    "\"başka hangi notta chunk geçiyor\" -> {\"intent\":\"notes\",\"query\":\"Re-ranking ve chunk başka hangi notta geçiyor?\"}\n"
    "\"peki gemini?\" -> {\"intent\":\"notes\",\"query\":\"Gemini raporu Re-ranking için ne önermiş?\"}\n"
    "\"ya maliyeti?\" -> {\"intent\":\"notes\",\"query\":\"Re-ranking maliyeti nedir?\"}\n"
    "\"hangi araçlarla yapılıyor\" -> {\"intent\":\"notes\",\"query\":\"Re-ranking hangi araçlarla yapılıyor?\"}\n"
    "\"kısaca anlat\" -> {\"intent\":\"followup\",\"query\":\"kısaca anlat\"}\n"
    "\"özetini çıkar\" -> {\"intent\":\"followup\",\"query\":\"özetini çıkar\"}\n"
    "\"doğru mu?\" -> {\"intent\":\"followup\",\"query\":\"doğru mu?\"}\n"
    "\"kimsin sen\" -> {\"intent\":\"meta\",\"query\":\"kimsin sen\"}"
)


def _parse(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(d, dict):
        return None
    intent = str(d.get("intent", "")).strip().lower()
    query = d.get("query")
    if intent not in _INTENTS or not isinstance(query, str):
        return None
    query = _clean(query)
    if not query:
        return None
    return {"intent": intent, "query": query}


def _last_answer(history: list[dict]) -> str:
    return next((m["content"] for m in reversed(history) if m.get("role") == "assistant"), "")


def _fallback(question: str, history: list[dict]) -> dict:
    return {"intent": route(question, True), "query": condense(question, history)}


def analyze(question: str, history: list[dict]) -> dict:
    """{"intent": followup|sources|notes|meta, "query": str}. Asla exception fırlatmaz.
    Geçmiş yoksa kural yolu (LLM yok); varsa kural ön-kontrolleri, sonra TEK LLM çağrısı."""
    try:
        if not history:
            return {"intent": route(question), "query": question}
        if route(question) == "meta":
            return {"intent": "meta", "query": question}
        if is_sources(question):
            return {"intent": "sources", "query": question}
        if route(question, True) == "followup":  # kesin kural kalıpları LLM'den önce
            return {"intent": "followup", "query": question}
        convo = "\n".join(
            f"{'Kullanıcı' if m['role'] == 'user' else 'Asistan'}: {m['content']}" for m in history)
        resp = llm.chat(
            messages=[{"role": "system", "content": INTENT_SYSTEM},
                      {"role": "user", "content": f"Geçmiş:\n{convo}\n\nSon mesaj: {question}\n\nJSON:"}],
            options={**config.LLM_OPTIONS, "temperature": 0, "num_predict": 96},
            keep_alive=config.LLM_KEEP_ALIVE, think=False, format="json",
        )
        out = _parse(resp["message"]["content"])
        if out is None:
            return _fallback(question, history)
        if out["intent"] == "followup" and has_new_content(question, _last_answer(history)):
            out["intent"] = "notes"  # yeni içerik sözcüğü var: önceki cevaptan yanıtlanamaz
        if not _valid(out["query"], question):
            out["query"] = question
        if out["intent"] in ("followup", "meta"):
            out["query"] = question
        return out
    except Exception:
        try:
            return _fallback(question, history)
        except Exception:
            return {"intent": "notes", "query": question}
