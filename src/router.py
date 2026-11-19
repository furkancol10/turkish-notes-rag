"""ADIM 0 - YÖNLENDİR: Soru notlarda aranmalı mı, yoksa asistanın kendisiyle ilgili mi?

Kural tabanlı ve temkinli: emin değilsek "notes" döner (normal RAG akışı).
"""
import re

# Pattern'lar normalize edilmiş (küçük harf, noktalamasız) metinde aranır.
# Tamamı eşleşmeli (fullmatch); "python nedir" gibi konulu sorular böylece notlara gider.
_META = [
    # selamlaşma
    r"(merhaba|selam|selamlar|meraba|hey|hi|hello|günaydın|iyi günler|iyi akşamlar|iyi geceler)( (nasılsın|nasılsınız|asistan))?",
    r"(naber|nasılsın|nasılsınız|ne haber|nbr)",
    # teşekkür / veda
    r"(teşekkürler|teşekkür ederim|sağ ol|sağol|eyvallah|çok teşekkürler|tşk|mersi)( (sana|asistan|çok))*",
    r"(görüşürüz|hoşça kal|hoşçakal|bay bay|iyi günler)",
    # kimlik
    r"(sen kimsin|kimsin sen|kimsin|sen nesin|adın ne|adın nedir|ismin ne|ismin nedir|bu ne|bu nedir)",
    r"(sen) (bir )?(yapay zeka|bot|asistan|yapay zekâ)(mısın)?",
    # yetenek
    r"(ne yapabilirsin|neler yapabilirsin|ne işe yarıyorsun|ne işe yarar|bana nasıl yardımcı olabilirsin|neler yapıyorsun|ne yaparsın)",
    r"(bana )?(nasıl )?yardım(cı)? (edebilir misin|olabilir misin|et)",
    # nasıl çalışıyor
    r"(sen |bu |bu uygulama |bu sistem )?nasıl çalışıyorsun|(bu )?(uygulama|sistem|program) nasıl çalışıyor",
    # model
    r"(sen )?(hangi|ne) (llm|dil modeli|modeli|model|yapay zeka modelini|yapay zeka)( modelini)? (kullanıyorsun|kullanıyor|tabanlısın)",
    r"(hangi|ne) (embedding|gömme) (modelini|modeli) (kullanıyorsun|kullanıyor)",
    r"(arkanda|arkada) (hangi|ne) (model|llm) (var|çalışıyor)",
    r"(sen )?(chatgpt|gpt|claude|gemini)( mi| misin)+( sen)?",
    r"(internete|internet'e) bağlı mısın",
]
_META_RE = [re.compile(p) for p in _META]


def normalize(text: str) -> str:
    # Türkçe-uyumlu küçük harf: İ -> i, I -> ı (Python'un lower()'ı bunu yanlış yapar)
    text = text.replace("İ", "i").replace("I", "ı").lower()
    text = re.sub(r"[^\w\s]", " ", text)        # noktalamayı at
    return re.sub(r"\s+", " ", text).strip()


def route(question: str) -> str:
    """"meta" (asistanla ilgili / sohbet) veya "notes" (notlarda ara) döner."""
    q = normalize(question)
    if q and any(r.fullmatch(q) for r in _META_RE):
        return "meta"
    return "notes"
