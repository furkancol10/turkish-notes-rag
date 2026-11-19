"""ADIM 0 - YÖNLENDİR: Soru notlarda aranmalı mı, yoksa asistanın kendisiyle ilgili mi?

Kural tabanlı ve temkinli: emin değilsek "notes" döner (normal RAG akışı).
Metin ASCII'ye katlanır (ç->c, ğ->g, ı->i ...), böylece "nasilsin" ile "nasılsın" aynıdır;
bu yüzden aşağıdaki pattern'lar ASCII yazılır.
"""
import re

_FOLD = str.maketrans("çğıöşüâîû", "cgiosuaiu")
_FILLER = {"ya", "yaa", "acaba", "lutfen", "bi", "bakalim", "canim", "abi", "kanka",
           "kardesim", "hocam", "dostum", "pls"}

# Tamamı eşleşmeli (fullmatch): "python nedir" / "teşekkür mektubu nasıl yazılır" gibi
# konulu sorular böylece notlara gider. Dolgu sözcükleri (_FILLER) önce atılır.
_MERHABA = r"(merhaba|merhabalar|meraba|selam|selamlar|slm|sa|hey|hi|hello|gunaydin|iyi (gunler|aksamlar|geceler|sabahlar))"
_NASILSIN = r"(nasilsin|nasilsiniz|naber|nbr|ne haber|ne var ne yok|nasil gidiyor)"
_META = [
    # selamlaşma ("merhaba nasılsın", "selam naber")
    rf"{_MERHABA}( asistan| {_NASILSIN})?",
    _NASILSIN,
    # teşekkür / veda
    r"(cok )?(tesekkur(ler)?( ederim)?|sag ol(un|asin)?|sagol(un|asin)?|eyvallah|tsk|mersi|saol)( (sana|cok))*",
    r"(gorusuruz|hosca kal|hosca kalin|bay bay|bye|iyi gunler)",
    # kimlik
    r"(sen )?(kimsin|nesin|neysin)( sen)?",
    r"(adin|ismin) (ne|nedir)",
    r"(kendini tanit(ir misin)?|kendinden bahset|kendini anlat|tanisalim)",
    r"sen (bir )?(yapay zeka|bot|asistan|insan|robot|program) (misin|musun)",
    r"(seni )?kim (yapti|yazdi|gelistirdi|olusturdu)( seni)?",
    r"(seni )?kim (tarafindan )?(yapildin|yazildin|gelistirildin)",
    # yetenek
    r"(ne|neler) (yapabilirsin|yapabiliyorsun|yaparsin|yapiyorsun)",
    r"ne ise yariyorsun|ne ise yarar(sin)?",
    r"(bana )?(nasil )?yardim(ci)? (edebilir misin|olabilir misin|olur musun|eder misin|et)",
    r"(bana )?nasil yardimci olabilirsin",
    # nasıl çalışıyor
    r"(sen |bu |bu uygulama |bu sistem )?nasil calisiyorsun",
    r"(bu )?(uygulama|sistem|program) nasil calisiyor",
    # model / gizlilik
    r"(sen )?(hangi|ne) (llm|dil modeli|dil modelini|modeli|modelini|model|yapay zeka modelini|yapay zeka)( modelini)?( kullaniyorsun| kullaniyor| tabanlisin)?",
    r"(hangi|ne) (embedding|gomme) (modelini|modeli) (kullaniyorsun|kullaniyor)",
    r"(arkanda|arkada) (hangi|ne) (model|llm) (var|calisiyor)",
    r"(sen )?(chatgpt|gpt|claude|gemini)( mi| misin)+( sen)?",
    r"(internete|internet) (bagli misin|kullaniyor musun|kullaniyor mu)",
    r"(verilerim|notlarim|veriler) (disari gidiyor mu|internete gidiyor mu|guvende mi)",
]
# "hangi dil modeli" tek başına meta sayılmasın diye kullanım eki zorunlu yapılmadı;
# ancak "hangi dil modeli daha iyi" gibi devamlı cümleler fullmatch'e takılıp notes'a gider.
_META_RE = [re.compile(p) for p in _META]


def normalize(text: str) -> str:
    # Türkçe-uyumlu küçük harf (İ -> i, I -> ı; Python'un lower()'ı bunu yanlış yapar),
    # sonra ASCII'ye katla, emoji/noktalamayı at, dolgu sözcüklerini çıkar.
    text = text.replace("İ", "i").replace("I", "ı").lower().translate(_FOLD)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = [w for w in text.split() if w not in _FILLER]
    return " ".join(words)


def route(question: str) -> str:
    """"meta" (asistanla ilgili / sohbet) veya "notes" (notlarda ara) döner."""
    q = normalize(question)
    if q and any(r.fullmatch(q) for r in _META_RE):
        return "meta"
    return "notes"
