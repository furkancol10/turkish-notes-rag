from types import SimpleNamespace

import pytest

from desktop import services
from src import config, entities
from src.entities import extract, missing, present


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
