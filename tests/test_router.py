import pytest

from src.router import route

META = ["merhaba", "Merhaba!", "selam", "Teşekkürler", "teşekkür ederim", "sağ ol", "sen kimsin",
        "Sen kimsin?", "SEN KİMSİN", "ne yapabilirsin", "Neler yapabilirsin?",
        "hangi modeli kullanıyorsun", "Hangi modeli kullanıyorsun?", "nasıl çalışıyorsun",
        "günaydın", "NASILSIN", "adın ne", "hangi llm kullanıyorsun", "iyi akşamlar", "naber"]

NOTES = ["Python nedir", "kimsin filmi", "Merhaba dünya programı nasıl yazılır",
         "RAG nedir", "hangi modeli kullanmalıyım", "teşekkür mektubu nasıl yazılır",
         "toplantı notlarında ne yapabilirsin kararı vardı", "embedding nedir",
         "Docker nasıl çalışıyor", "selam vermek için hangi kod kullanılır", "", "?!",
         "bge-m3 modelinin boyutu kaç", "yarınki toplantı ne zaman", "sen kimsin filmindeki oyuncular",
         "hangi modeli seçtik", "nasıl çalışır vektör arama", "kim kazandı", "ne yapmalıyım",
         "Kimsin filminin yönetmeni kim"]

META += ['kendini tanıt', 'kendini tanıtır mısın', 'nasılsın', 'nasılsın ya', 'naber', 'naber ya', 'nasilsin', 'sen bir yapay zeka mısın', 'sen yapay zeka mısın', 'neler yapabiliyorsun?', 'neler yapabiliyorsun', 'bana nasıl yardımcı olabilirsin', 'bana nasil yardimci olabilirsin', 'kim yaptı seni', 'seni kim yaptı', 'hangi dil modeli', 'hangi dil modelini kullanıyorsun', 'selamlar', 'iyi akşamlar', 'sağ ol', 'sag ol', 'eyvallah', 'sen kimsin ya', 'sen kimsin acaba', 'merhaba 👋', 'selam 😊', 'teşekkürler 🙏', 'tesekkur ederim', 'çok sağ ol', 'kimsin sen', 'ne işe yarıyorsun', 'merhabalar', 'slm', 'sen neysin', 'hangi modeli kullanıyorsun', 'nasıl çalışıyorsun', 'nasil calisiyorsun', 'günaydın', 'hoşça kal', 'görüşürüz', 'sen chatgpt misin', 'merhaba nasılsın', 'selam naber', 'ne yapabilirsin acaba', 'yardımcı olur musun', 'bana yardım eder misin', 'internet kullanıyor musun', 'verilerim dışarı gidiyor mu', 'adın ne ya', 'tanışalım', 'sen insan mısın', 'sağ olasın']
NOTES += ['yapay zeka nedir', 'dil modeli nasıl eğitilir', 'teşekkür mektubu nasıl yazılır', 'merhaba kelimesinin kökeni', 'model nedir istatistikte', 'selam vermek nasıl olur', 'python nedir', 'embedding modeli nedir', 'hangi dil modeli daha iyi', 'kimsin sen diye başlayan şiir notum', 'bot nasıl yazılır', 'nasılsın sorusuna ingilizce cevap nedir', 'yapay zeka etiği hakkında ne yazmıştım', 'rag nasıl çalışır', 'toplantı notlarım neler', 'llm nedir', 'yardım istemek için ne yapmalıyım', 'neler yapabilirim bu hafta', 'bana nasıl yardımcı olabilirsin sorusuna cevap örnekleri', 'gpt nedir', 'claude kimdir', 'sen kimsin romanı özeti', 'hangi model kullanılmalı sınıflandırma için', 'iyi akşamlar yemeği tarifi', 'eyvallah kelimesi nereden gelir', 'mersi ne demek', 'kim yaptı bu projeyi notlarda', 'uygulama nasıl çalışıyor docker', 'naber kelimesi']


@pytest.mark.parametrize("q", META)
def test_meta(q):
    assert route(q) == "meta"


@pytest.mark.parametrize("q", NOTES)
def test_notes(q):
    assert route(q) == "notes"

# Uygulama kullanımı soruları meta; konu soruları notes kalmalı
APP_META = ["yeni not nasıl eklerim?", "not nereden eklenir", "notlarımı nasıl yüklerim",
            "nasıl yeniden indekslerim", "indeksleme nasıl yapılır"]
APP_NOTES = ["not almanın faydaları nedir", "dosya sıkıştırma nasıl çalışır", "indeks fonu nedir"]


@pytest.mark.parametrize("q", APP_META)
def test_app_usage_meta(q):
    assert route(q) == "meta"


@pytest.mark.parametrize("q", APP_NOTES)
def test_app_usage_topic_stays_notes(q):
    assert route(q) == "notes"


FOLLOWUP = ["doğru mu", "Bu doğru mu?", "emin misin", "Emin misin?", "yanlış değil mi", "kesin mi",
            "daha kısa anlat", "özetle", "Özetler misin", "madde madde yaz", "tablo yap",
            "basitçe anlat", "2. maddeyi açıkla", "ilkini detaylandır", "neden", "Niye?",
            "kaynağın ne", "nereden buldun", "hangi nottan aldın", "bunu açıkla", "daha basit anlat",
            "gerçekten mi", "3. maddeyi detaylandır"]
TRAPS = ["peki gemini ne önermiş", "ilki ne zorlukta", "neden python popüler", "daha kısa sürede nasıl öğrenirim",
         "özetle toplantı notlarını", "kaynak kod nerede", "tablo oluşturma notum var mı",
         "docker nedir", "madde madde yazdığım liste nerede", "emin olmadığım konular neler",
         "doğru dürüst bir plan var mı", "gemini raporunda neler var", "kaynak yönetimi nasıl yapılır",
         "bunun maliyeti ne kadar", "onun süresi ne", "yarınki toplantı ne zaman", "peki ya claude",
         "basit bir RAG nasıl kurulur", "neden bge-m3 seçtik"]


@pytest.mark.parametrize("q", FOLLOWUP)
def test_followup_with_history(q):
    assert route(q, has_history=True) == "followup"


@pytest.mark.parametrize("q", FOLLOWUP)
def test_followup_phrases_without_history_are_notes(q):
    assert route(q) == "notes"
    assert route(q, has_history=False) == "notes"


@pytest.mark.parametrize("q", TRAPS)
def test_traps_stay_notes_with_history(q):
    assert route(q, has_history=True) == "notes"


@pytest.mark.parametrize("q", META[:20])
def test_meta_still_meta_with_history(q):
    assert route(q, has_history=True) == "meta"
