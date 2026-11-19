from types import SimpleNamespace

import pytest

from desktop import services
from src import config, entities
from src.entities import extract, missing, present


V = {"bugün", "toplantıda", "kitap", "python", "bütçe", "ne"}


@pytest.mark.parametrize("q,exp", [
    ("Zeynep ne dedi?", ["Zeynep"]), ("Mehmet Bey ne dedi?", ["Mehmet"]), ("Ayşe'nin doğum günü ne zaman?", ["Ayşe"]),
    ("Bugün ne yaptım?", []), ("Toplantıda ne konuştuk?", []), ("Kitap önerin var mı?", []),
    ("Python demetleri nedir?", []), ("What did you say?", []), ("Who is Ali?", ["Ali"]),
])
def test_sentence_initial_names(q, exp):
    assert extract(q, vocab=V) == exp


@pytest.mark.parametrize("q", ["Bugün ne yaptım?", "Toplantıda ne konuştuk?", "Kitap önerin var mı?"])
def test_builtin_common_without_corpus(q):
    assert extract(q, vocab=set()) == []


def test_initial_suffixed_stop():
    assert extract("Yazarın meditasyon türü neydi?", vocab=V) == []


def test_initial_name_missing():
    assert missing("Zeynep ne dedi?", ["ali evet dedi"], vocab=V) == ["Zeynep"]
    assert missing("Mehmet Bey ne dedi?", ["ali evet dedi"], vocab=V) == ["Mehmet"]
    assert extract("Mehmet Bey ne dedi?", vocab=V) == ["Mehmet"]


def test_sentence_initial_ignored():
    assert extract("Bütçe ne kadar?") == []
    assert extract("Hangi gün Python öğrendim?") == ["Python"]


def test_turkish_suffix_and_apostrophe():
    assert extract("Proje Nova'nın test aşaması ne zaman?") == ["Nova"]
    assert extract("Ayşe'nin doğum günü ne zaman?") == ["Ayşe"]
    assert extract("Simyacı'nın yazarı kim?") == ["Simyacı"]      # cümle başı ama kesme işaretli
    assert extract("Işık'ın notu ne?") == ["Işık"]


def test_multiword_quoted_code():
    assert extract("Dün Ahmet Yılmaz ile ne konuştum?") == ["Ahmet Yılmaz"]
    assert extract('"Kırmızı Plan" nedir?') == ["Kırmızı Plan"]
    assert extract("RTX4090 kaç watt çekiyor?") == ["RTX4090"]


def test_generic_words_dropped():
    assert extract("Bugün Ocak ayında Proje ne durumda?") == []
    assert extract("Bana Nedir bu Türkiye hakkında?") == []


def test_catalog_excluded():
    from src.doc_filter import build_catalog
    cat = build_catalog(["proje_nova.md"], {"proje_nova.md": "Nova"})
    assert extract("Dün Nova'nın bütçesi ne?", cat) == []
    assert extract("Dün Atlas'ın bütçesi ne?", cat) == ["Atlas"]


def test_present_suffixes():
    assert present("Nova", ["Proje Novanın bütçesi"])
    assert present("Ayşe", ["Ayşe'nin kedisi"])
    assert present("Eskişehir", ["eskişehirde gezdik"])
    assert present("Ahmet Yılmaz", ["Ahmet ve Yılmaz"])
    assert not present("Atlas", ["Proje Nova bütçesi"])
    assert not present("Ali", ["Alinin evi"])                    # kısa ad: yalnız tam eşleşme
    assert present("RTX4090", ["rtx4090 kartı"])


def test_missing():
    assert missing("Proje Atlas'ın katılımcıları kim?", ["Proje Nova katılımcıları"]) == ["Atlas"]
    assert missing("Proje Atlas'ın katılımcıları kim?", ["Atlas ekibi"]) == []
    assert missing("katılımcılar kim?", ["x"]) == []              # varlık yok: koruma yok


CH = SimpleNamespace(id="a#0", source="a.md", heading="H", page=0, text="Proje Nova bütçesi 450 bin TL")


@pytest.fixture
def env(monkeypatch):
    c = {"llm": 0}
    monkeypatch.setattr(services, "load_embed_model", lambda: None)
    monkeypatch.setattr(services, "index_status", lambda: object())
    monkeypatch.setattr(services, "analyze", lambda q, h: {"intent": "notes", "query": q})
    monkeypatch.setattr(services, "retrieve", lambda q, k, backend: [(CH, 0.8)])
    monkeypatch.setattr(services, "_doc_catalog", lambda b: None)

    def ans(q, r, h=None):
        c["llm"] += 1
        return "cevap"
    monkeypatch.setattr(services, "answer", ans)
    return c


def test_guard_blocks_llm(env, monkeypatch):
    monkeypatch.setattr(config, "ENTITY_GUARD_ENABLED", True)
    a, res, info = services.ask("Proje Atlas'ın bütçesi ne?", 10, "numpy", [], 0.4, True)
    assert a == services.NOT_IN_NOTES and env["llm"] == 0
    assert info["entity_missing"] == ["Atlas"] and "Atlas" in info["note"] and res


def test_guard_off_calls_llm(env, monkeypatch):
    monkeypatch.setattr(config, "ENTITY_GUARD_ENABLED", False)
    a, _, info = services.ask("Proje Atlas'ın bütçesi ne?", 10, "numpy", [], 0.4, True)
    assert a == "cevap" and env["llm"] == 1 and "entity_missing" not in info


def test_guard_passes_when_present(env, monkeypatch):
    monkeypatch.setattr(config, "ENTITY_GUARD_ENABLED", True)
    a, _, _ = services.ask("Proje Nova'nın bütçesi ne?", 10, "numpy", [], 0.4, True)
    assert a == "cevap" and env["llm"] == 1


@pytest.mark.parametrize("q,text", [
    ("Bu hafta 5km koştum mu?", "bu hafta 5 km'yi koştum"),
    ("Ali Bey ne dedi?", "Ali toplantıda dedi ki"),
    ("What did I eat?", "pasta yedim"),
    ("Geçen Hafta Toplantıda ne konuştuk?", "toplantıda bütçe konuşuldu"),
    ("Dr. Ayşe ne dedi?", "Ayşe bugün geldi"),
    ("Proje Nova'nın bütçesi ne?", "Nova bütçesi 5 bin"),
    ("2025 bütçesi ne kadar?", "2025 bütçesi 10 bin"),
    ("When did We meet?", "toplantı yaptık"),
])
def test_not_false_missing(q, text):
    assert missing(q, [text]) == []


def test_real_missing_still_detected():
    assert missing("Zeynep'in doğum günü ne zaman?", ["Ali'nin doğum günü mayısta"]) == ["Zeynep"]


def test_extract_strips_stop_and_short():
    assert extract("Ali Bey ne dedi?", vocab=V) == ["Ali"]
    assert extract("Dün Ali Bey ne dedi?", vocab=V) == ["Ali"]
    assert extract("What did I eat?") == []
    assert extract("Geçen Hafta Toplantıda ne konuştuk?") == []
