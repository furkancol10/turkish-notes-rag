import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "eval" / "followup_questions.json").read_text("utf-8"))
INTENTS = {"notes", "followup", "sources", "meta"}


def test_conversations_schema():
    assert len(DATA) >= 25
    ids = [c["id"] for c in DATA]
    assert len(ids) == len(set(ids))
    for c in DATA:
        assert 2 <= len(c["turns"]) <= 3
        assert c["turns"][0]["expected_intent"] in {"notes", "meta"}
        for t in c["turns"]:
            assert t["question"].strip() and t["reference_answer"].strip()
            assert t["expected_intent"] in INTENTS
            src = t["expected_source"]
            if t["expected_intent"] in {"notes", "sources"}:
                assert src
            if src:
                assert (ROOT / "data" / "notes" / src).exists(), src
            if "query_keyword" in t:
                assert t["expected_intent"] == "notes" and t["query_keyword"].strip()


def test_intent_mix():
    intents = {t["expected_intent"] for c in DATA for t in c["turns"]}
    assert intents == INTENTS
    assert sum(t["expected_intent"] == "sources" for c in DATA for t in c["turns"]) >= 6
