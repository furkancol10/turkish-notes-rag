import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "eval" / "mixing_questions.json").read_text("utf-8"))
DOCS = ROOT.parent / "Katalog" / "Docs"


def test_schema():
    assert len(DATA) >= 30
    assert len({d["question"] for d in DATA}) == len(DATA)
    for d in DATA:
        assert d["corpus"] in {"notes", "docs"} and d["question"].strip()
        if d["comparison"]:
            assert len(d["allowed_docs"]) == 2
        else:
            assert len(d["allowed_docs"]) == 1 and 1 <= len(d["key_facts"]) <= 3
        if d["corpus"] == "notes":
            assert all((ROOT / "data" / "notes" / f).exists() for f in d["allowed_docs"]), d
        elif DOCS.exists():
            assert all(list(DOCS.glob(f + ".*")) for f in d["allowed_docs"]), d


def test_mix():
    assert sum(d["comparison"] for d in DATA) >= 6
    assert {d["corpus"] for d in DATA} == {"notes", "docs"}


def test_helpers():
    from eval.run_mixing_eval import fold, purity
    assert fold("İMAM Bayıldı") == "imam bayildi"
    assert purity(["a.pdf", "a.html", "b.pdf"], {"a"}) == 2 / 3
