"""Held-out niyet seti (ayarlama sırasında kullanılmadı): uv run python -m eval.run_heldout_intent"""
import json
from pathlib import Path

from src.rewriter import analyze

data = json.loads((Path(__file__).parent / "heldout_intent.json").read_text("utf-8"))
ok = n = 0
for conv in data:
    hist = [m for q, a in conv["history"] for m in ({"role": "user", "content": q}, {"role": "assistant", "content": a})]
    for t in conv["turns"]:
        got = analyze(t["question"], hist)["intent"]
        n += 1
        ok += got == t["expected_intent"]
        if got != t["expected_intent"]:
            print(f"MISS {t['question']!r}: beklenen {t['expected_intent']}, tahmin {got}")
print(f"held-out: {ok}/{n} = {ok / n:.2f}")
