import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "eval" / "general_frozen.json").read_text("utf-8"))


def test_general_frozen_schema():
    assert D["frozen"] is True and D["expected_filter"] is None
    qs = D["questions"]
    assert len(qs) >= 20
    assert len({q["q"] for q in qs}) == len(qs) and len({q["id"] for q in qs}) == len(qs)
    assert all(q["q"].strip().endswith("?") for q in qs)


def test_no_overlap_with_mixing_set():
    m = {d["question"] for d in json.loads((ROOT / "eval" / "mixing_questions.json").read_text("utf-8"))}
    assert not m & {q["q"] for q in D["questions"]}


def test_score_helper():
    from eval.run_filter_eval import score
    items = [{"corpus": "notes", "question": "a", "allowed_docs": ["x.md"]}]
    hr, wr, _, wrong = score(items, [{"q": "g1"}, {"q": "g2"}], lambda q: ["x.md"] if q in ("a", "g1") else None)
    assert hr == 1 and wr == 0.5 and wrong == [("g1", ["x.md"])]


def test_entity_eval_uses_tmp_index(tmp_path, monkeypatch):
    import subprocess, sys
    real = ROOT / "data" / "index"
    before = sorted((str(p), p.stat().st_mtime) for p in real.rglob("*")) if real.exists() else []
    r = subprocess.run([sys.executable, "-m", "eval.run_entity_eval", "--guard", "on", "--out", str(tmp_path / "o.json"), "--dry"],
                       cwd=ROOT, capture_output=True, text=True, env={**__import__("os").environ, "HOME": str(tmp_path)})
    assert r.returncode == 0, r.stderr
    assert "entity_eval_" in r.stdout and "0.4" in r.stdout and str(real) not in r.stdout
    after = sorted((str(p), p.stat().st_mtime) for p in real.rglob("*")) if real.exists() else []
    assert before == after
