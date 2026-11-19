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
    # uygulama kullanımı (not ekleme / indeksleme)
    r"(yeni )?(not|notlarimi|notlari|dosya) (nasil|nereden|nereye) (eklerim|eklenir|ekleyebilirim|yuklerim|yuklenir|yukleyebilirim)",
    r"(notlarimi |notlari )?(nasil )?(yeniden )?indekslerim|indeksleme nasil yapilir|ne zaman indekslemeliyim",
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


_ORD = r"(\d+|ilk|ikinci|ucuncu|dorduncu|besinci|son|birinci)"
_FOLLOWUP = [
    # doğruluk / güven
    r"(bu |bunlar |bundan |cevabindan |cevabin )?(dogru mu|dogru musun|emin misin|emin misiniz|kesin mi|kesin misin|gercekten mi|dogru degil mi|yanlis degil mi|yanlis mi|hatali mi|yanlis olmasin)( bu| sen)?",
    r"(bundan|bunun|cevabindan) (emin misin|dogru mu)",
    # biçim değiştirme
    r"(daha )?(kisa|kisaca|ozet|basit|sade|net|detayli|uzun)( (anlat|yaz|olur mu|olsun|ifade et|soyle|cevapla|anlatir misin|yazar misin))?",
    r"(bunu |cevabi |onu )?(kisalt|ozetle|ozetler misin|ozetle bakalim|sadelestir|basitlestir|tekrar yaz|yeniden yaz|tekrar anlat|baska turlu anlat)( misin)?",
    r"(bunu |onu |cevabi )?(madde madde|maddeler halinde|liste halinde|tablo halinde|tablo seklinde|liste yap|tablo yap|tabloya dok|listele)( (yaz|anlat|yap|goster|ver|yazar misin))?( misin)?",
    r"(bunu |onu |cevabi )?(kisa bir |kisa |kisaca )?(liste|tablo|madde) (yap|yaz|haline getir)( misin)?",
    r"(bunu |onu )?(basitce|sade bir dille|kisaca|ozetle) (anlat|acikla|yaz)( misin)?",
    r"(bunu )?(turkceye|ingilizceye) (cevir|cevirir misin)",
    # bir kısmı açma
    rf"{_ORD} (madde|maddeyi|maddeyi|maddesini|maddenin|maddesi)( hakkinda)?( daha)? (acikla|acikla misin|acar misin|detaylandir|detaylandirir misin|anlat|anlatir misin|ayrintilandir)",
    rf"{_ORD}(ni|yi|ini|sini|sunu|nu|u|si)? (biraz |daha )?(acikla|acikla misin|acar misin|detaylandir|detaylandirir misin|anlat|anlatir misin|ayrintilandir)",
    r"(bunu|onu|bunlari|bu kismi|bu maddeyi) (daha )?(acikla|acar misin|detaylandir|detaylandirir misin|ayrintilandir|genislet|aciklar misin|acikla misin)",
    r"(biraz |daha )?(detaylandir|detay ver|aciklar misin|acikla|genislet|devam et|devam)",
    r"(neden|niye|nicin|neden boyle|neden oyle|neden peki|neden yani|peki neden|yani neden|nasil yani)",
    # kaynak
    r"(kaynagin|kaynak|kaynaklarin|kaynagini|kaynaklari) (ne|neydi|nedir|nerede|goster|ver|hangisi|hangileri)( misin)?",
    r"(bunu |bu bilgiyi |bunu |onu )?(nereden|nerden) (buldun|aldin|cikardin|biliyorsun|ogrendin)",
    r"(hangi|ne) (nottan|notlardan|dosyadan|kaynaktan) (aldin|buldun|cikardin|geliyor)( bunu)?",
    r"(bunu |bu bilgiyi )?(hangi|ne) (nottan|notlardan|dosyadan|kaynaktan) (aldin|buldun|cikardin|geliyor|geldi)",
    r"(bunu )?(kaynak goster|kaynagi goster|kaynak ver)",
]
_FOLLOWUP_RE = [re.compile(p) for p in _FOLLOWUP]


# --- Kaynak soruları: "önceki cevap hangi dosyadan/sayfadan geldi?" (yalnızca geçmiş varken) ---
# Sadece ÖNCEKİ cevaba gönderme yapan kalıplar (bu/bundan/bunu/zamir ya da fiilsiz kısa); konulu
# ("toplantı notları hangi dosyada var") sorular LLM sınıflandırıcısına bırakılır.
_SRC_NOUN = r"(dosya|dosyada|dosyda|dosyadan|dosyadaydi|not|notta|nottan|notlarda|notlardan|belge|belgede|belgeden|rapor|raporda|raporlarda|rapordan|sayfa|sayfada|sayfadan|pdf|pdfte|pdfde|kaynak|kaynakta|kaynaktan|yerde|yerden)"
_SRC_THIS = r"(bu|bunu|bunlari|bundan|bunun|onu|ondan|bu konu|bu konuyu|bu konudan|bu bilgi|bu bilgiyi|bu bilgiden|bu cevap|bu cevabi)"
_SRC_VERB = r"(bahsetmis|bahsediyor|bahseder|bahsedilmis|geciyor|gecer|gecmis|yaziyor|yazmis|yaziyordu|var|vardi|anlatiyor|anlatmis|anlatilmis|belirtmis|belirtiliyor|yer aliyor|ifade ediliyor|soyluyor|soylenmis|mevcut|aciklanmis|aciklaniyor)"
_SOURCES = [
    rf"(peki |ya |bu |bunlar |bunu )?(hangi|ne) {_SRC_NOUN}( {_SRC_THIS})?( {_SRC_VERB})?( {_SRC_THIS})?( mu| mi)?",
    rf"(peki |ya )?{_SRC_THIS} (hangi|ne) {_SRC_NOUN}( {_SRC_VERB})?( mu| mi)?",
    rf"(peki |ya )?(hangi|ne) {_SRC_NOUN} (icinde|icerisinde|icin)( {_SRC_THIS})?( {_SRC_VERB})?",
    # kaynağın ne / kaynaklar neler
    r"(peki |ya )?(bunun |bunlarin |cevabin |cevabinin )?(kaynagin|kaynak|kaynaklarin|kaynaklar|kaynagini|kaynaklari|kaynagi)( ne| neydi| nedir| neler| nerede| nelerdi| neresi| hangisi| hangileri| goster| ver)( misin)?",
    r"(kaynak|kaynaklar|dosya|dosyalar|dosya adi) (goster|ver|goster bana|listele|neler)",
    # nereden buldun
    r"(bunu |bu bilgiyi |bu cevabi |onu )?(nereden|nerden|neresinden|nereden aldin) ?(buldun|aldin|cikardin|biliyorsun|ogrendin|geldi|geliyor|aldin bunu|buldun bunu)?",
    # bu hangi dosya / sayfa
    r"(bu|bunlar) (hangi )?(dosya|dosyalar|not|notlar|belge|belgeler|rapor|raporlar|sayfa|sayfalar)(dan|den|tan|ten)? (geliyor|geldi|alindi)",
    rf"(peki |ya )?(bu |bunlar )?(hangi )?(dosya|sayfa|not|belge|rapor|pdf)( numarasi| adi| ismi)? (neydi|ne|hangisi|hangisiydi)",
    r"(hangi|ne) (dosya|dosyayi|notu|notlari|belgeyi|raporu|sayfayi|kaynagi|kaynaklari) (kullandin|kullanarak|temel aldin|baz aldin|okudun|inceledin)( bunun icin)?",
    r"(bunu )?(hangi )?(dosyalara|notlara|kaynaklara|sayfalara) (baktin|dayanarak|dayaniyor)",
]
_SOURCES_RE = [re.compile(p) for p in _SOURCES]


def is_sources(question: str) -> bool:
    """Önceki cevabın kaynağını (dosya/sayfa/not) soran kalıp mı? (kural tabanlı, LLM'siz)"""
    q = normalize(question)
    return bool(q) and any(r.fullmatch(q) for r in _SOURCES_RE)


def route(question: str, has_history: bool = False) -> str:
    """"meta" (asistanla ilgili / sohbet), "followup" (önceki cevabın kendisi hakkında;
    yalnızca geçmiş varken), "sources" (önceki cevabın hangi dosya/sayfadan geldiği; yalnızca
    geçmiş varken, _SOURCES kalıpları; eski _FOLLOWUP kaynak kalıpları "followup" olarak kalır)
    veya "notes" (notlarda ara) döner."""
    q = normalize(question)
    if q and any(r.fullmatch(q) for r in _META_RE):
        return "meta"
    if has_history and q and any(r.fullmatch(q) for r in _FOLLOWUP_RE):
        return "followup"
    if has_history and is_sources(question):
        return "sources"
    return "notes"
