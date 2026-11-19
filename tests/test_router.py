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
