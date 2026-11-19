import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "eval" / "followup_questions.json").read_text("utf-8"))
ROUTES = {"notes", "followup", "meta"}


def test_conversations_schema():
    assert len(DATA) >= 12
    ids = [c["id"] for c in DATA]
    assert len(ids) == len(set(ids))
    for c in DATA:
        assert 2 <= len(c["turns"]) <= 3
        assert c["turns"][0]["expected_route"] != "followup"
        for t in c["turns"]:
            assert t["question"].strip() and t["reference_answer"].strip()
            assert t["expected_route"] in ROUTES
            src = t["expected_source"]
            if t["expected_route"] == "notes":
                assert src
            if src:
                assert (ROOT / "data" / "notes" / src).exists(), src


def test_route_mix():
    routes = {t["expected_route"] for c in DATA for t in c["turns"]}
    assert routes == ROUTES
