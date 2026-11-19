from types import SimpleNamespace

from src import generator


def _c(src, text, page=0, heading=""):
    return SimpleNamespace(source=src, heading=heading, page=page, text=text)


RES = [(_c("gemini.pdf", "G1", 2), 0.9), (_c("gpt.pdf", "P1", 1, "Bölüm"), 0.95),
       (_c("gemini.pdf", "G2", 3), 0.5), (_c("gpt.pdf", "P2"), 0.4)]


def test_grouping_order_and_global_numbers():
    p = generator.build_prompt("s?", RES)
    assert p.index("### Belge: gpt.pdf") < p.index("### Belge: gemini.pdf")
    assert p.count("### Belge:") == 2
    gpt, gem = p.split("### Belge: gemini.pdf")
    assert "[2]" in gpt and "[4]" in gpt and "[1]" not in gpt
    assert "[1] (s. 2)\nG1" in gem and "[3] (s. 3)\nG2" in gem
    assert "[2] (s. 1 / Bölüm)\nP1" in gpt and p.endswith("Soru: s?")


def test_system_rules():
    for k in ("### Belge", "birleştirme", "Bu bilgi notlarda yok", "tüm maddeleri", "sonuna"):
        assert k in generator.SYSTEM


def test_budget_respected(monkeypatch):
    got = {}
    monkeypatch.setattr(generator.ollama, "chat",
                        lambda **kw: got.update(kw) or {"message": {"content": "x"}})
    big = [(_c(f"d{i}.md", "a" * 900), 1 - i / 100) for i in range(30)]
    hist = [{"role": "user", "content": "q" * 300}, {"role": "assistant", "content": "w" * 300}]
    generator.answer("soru?", big, hist)
    m = got["messages"]
    total = sum(generator.conversation.approx_tokens(x["content"]) for x in m)
    assert total <= 3000
