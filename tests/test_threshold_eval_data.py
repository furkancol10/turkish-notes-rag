import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TUNE = json.loads((ROOT / "eval" / "threshold_questions.json").read_text("utf-8"))
FROZEN = json.loads((ROOT / "eval" / "threshold_frozen.json").read_text("utf-8"))
CATS = {"answerable", "off-topic", "near-miss", "entity-swap"}


def test_schema():
    for it in TUNE + FROZEN:
        assert set(it) == {"id", "q", "answerable", "category", "expected_source"}
        assert it["q"].strip() and it["category"] in CATS
        assert it["answerable"] == (it["category"] == "answerable")
        if it["answerable"]:
            assert (ROOT / "data" / "notes" / it["expected_source"]).exists()
        else:
            assert it["expected_source"] is None


def test_disjoint_and_balanced():
    ids = [i["id"] for i in TUNE + FROZEN]
    qs = [i["q"] for i in TUNE + FROZEN]
    assert len(ids) == len(set(ids)) and len(qs) == len(set(qs))
    for d in (TUNE, FROZEN):
        assert {i["category"] for i in d} == CATS
    assert sum(i["answerable"] for i in TUNE + FROZEN) >= 40
    assert sum(not i["answerable"] for i in TUNE + FROZEN) >= 40
    assert 0.55 <= len(TUNE) / (len(TUNE) + len(FROZEN)) <= 0.65


def test_split_is_deterministic_hash_rule():
    for cat in CATS:
        allc = sorted((i["id"] for i in TUNE + FROZEN if i["category"] == cat),
                      key=lambda x: hashlib.sha1(x.encode()).hexdigest())
        n = round(len(allc) * 0.6)
        assert {i["id"] for i in TUNE if i["category"] == cat} == set(allc[:n])
