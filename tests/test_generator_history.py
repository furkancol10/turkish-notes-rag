from types import SimpleNamespace

from src import generator


def _cap(monkeypatch):
    got = {}

    def chat(**kw):
        got.update(kw)
        return {"message": {"content": " cevap "}}
    monkeypatch.setattr(generator.ollama, "chat", chat)
    return got


def _res():
    return [(SimpleNamespace(source="a.md", heading="", page=None, text="metin"), 0.9)]


def test_answer_without_history(monkeypatch):
    got = _cap(monkeypatch)
    assert generator.answer("s?", _res()) == "cevap"
    roles = [m["role"] for m in got["messages"]]
    assert roles == ["system", "user"]


def test_answer_with_history(monkeypatch):
    got = _cap(monkeypatch)
    hist = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    generator.answer("s?", _res(), hist)
    msgs = got["messages"]
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"]
    assert "Önceki konuşma sadece soruyu anlamak" in msgs[0]["content"]
    assert "Bağlam:" in msgs[-1]["content"] and "Soru: s?" in msgs[-1]["content"]


def test_answer_followup(monkeypatch):
    got = _cap(monkeypatch)
    hist = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    srcs = [{"source": "x.md", "heading": "H", "page": 2, "text": "ilk"}, {"source": "y.md", "text": "ikinci"}]
    assert generator.answer_followup("doğru mu?", hist, srcs) == "cevap"
    msgs = got["messages"]
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"]
    last = msgs[-1]["content"]
    assert "[1] (x.md, H, s.2)\nilk" in last and "[2] (y.md)\nikinci" in last
    assert last.endswith("Soru: doğru mu?")
