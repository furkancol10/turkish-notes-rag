from types import SimpleNamespace

from src import conversation as cv


def _m(role, text):
    return {"role": role, "text": text, "sources": [{"source": "a"}]}


def test_window_order_turns_and_no_sources():
    msgs = []
    for i in range(5):
        msgs += [_m("user", f"soru{i}"), _m("assistant", f"cevap{i}")]
    w = cv.window(msgs, max_turns=2)
    assert [m["content"] for m in w] == ["soru3", "cevap3", "soru4", "cevap4"]
    assert all(set(m) == {"role", "content"} for m in w)


def test_window_strips_citations():
    w = cv.window([_m("user", "x"), _m("assistant", "Ali 5 yaşında [1]. Ve Veli [2, 3] de.")])
    assert w[1]["content"] == "Ali 5 yaşında. Ve Veli de."


def test_truncate_sentence_and_word():
    long = "Birinci cümle burada. " + "ikinci cümle uzun uzun devam ediyor " * 10
    w = cv.window([_m("user", "x"), _m("assistant", long)], max_answer_chars=60)
    assert w[1]["content"] == "Birinci cümle burada.…"
    w = cv.window([_m("user", "x"), _m("assistant", "kelime " * 50)], max_answer_chars=20)
    assert w[1]["content"].endswith("…") and "kelim…" not in w[1]["content"]
    assert len(w[1]["content"]) <= 21


def test_approx_tokens():
    assert cv.approx_tokens("a" * 30) == 10


def _res(n, size):
    return [(SimpleNamespace(source="a.md", heading="", page=None, text="x" * size), 0.5) for _ in range(n)]


def test_fit_budget_drops_history_first_then_chunks():
    hist = [{"role": "user", "content": "h" * 900}, {"role": "assistant", "content": "i" * 900},
            {"role": "user", "content": "j" * 90}]
    h, r = cv.fit_budget(hist, _res(5, 1200), "soru", limit=2300)
    assert len(r) == 5 and [x["content"][0] for x in h] == ["j"]
    h, r = cv.fit_budget(hist, _res(5, 1200), "soru", limit=900)
    assert h == [] and 0 < len(r) < 5
    # chunks dropped from the tail
    assert r == _res(5, 1200)[:len(r)]


def test_fit_budget_noop_when_small():
    hist = [{"role": "user", "content": "a"}]
    h, r = cv.fit_budget(hist, _res(2, 10), "q")
    assert h == hist and len(r) == 2
