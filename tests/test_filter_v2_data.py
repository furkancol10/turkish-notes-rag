import json
from pathlib import Path
E_ = Path(__file__).parent.parent / "eval"
NOTES = {p.stem for p in (Path(__file__).parent.parent / "data" / "notes").glob("*.md")}

def test_general_v2():
    d = json.loads((E_ / "general_frozen_v2.json").read_text("utf-8"))
    assert d["frozen"] is True and d["date"] and len(d["questions"]) >= 30
    assert all(q["q"].strip() for q in d["questions"])

def test_targeted_v2():
    d = json.loads((E_ / "doc_targeted_v2.json").read_text("utf-8"))
    assert d["frozen"] is True and len(d["questions"]) >= 20
    for q in d["questions"]:
        assert q["q"].strip() and q["docs"] and set(q["docs"]) <= NOTES
