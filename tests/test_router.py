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


@pytest.mark.parametrize("q", META)
def test_meta(q):
    assert route(q) == "meta"


@pytest.mark.parametrize("q", NOTES)
def test_notes(q):
    assert route(q) == "notes"
