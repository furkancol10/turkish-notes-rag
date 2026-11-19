"""Sadece geri getirme (retrieval) değerlendirmesi, LLM yok.
Çalıştır:  uv run python -m eval.run_eval
Metrikler: hit@k = doğru not ilk k parça içinde mi?  MRR = 1/(doğru notun ilk göründüğü sıra)."""
import json
from pathlib import Path

import numpy as np

from src import config
from src.chunker import chunk_docs
from src.embedder import embed_passages, embed_query
from src.loader import load_notes

K = 3
HERE = Path(__file__).parent
# Cevabı notlarda olmayan sorular (source=null) metriğe girmez; ask ile denenir.
questions = [x for x in json.loads((HERE / "questions.json").read_text("utf-8")) if x["source"]]
docs = load_notes()

rows = []
for model in config.EMBED_MODELS:
    qvecs = np.array([embed_query(x["q"], model) for x in questions])
    for size in (256, 512, 1024):
        chunks = chunk_docs(docs, "fixed", size, size // 8)
        vecs = embed_passages([c.text for c in chunks], model)
        hits, rr = 0, []
        for x, qv in zip(questions, qvecs):
            order = np.argsort(-(vecs @ qv))
            rank = next((r for r, i in enumerate(order, 1) if chunks[i].source == x["source"]), None)
            hits += rank is not None and rank <= K
            rr.append(1 / rank if rank else 0)
        rows.append((model, size, len(chunks), hits / len(questions), float(np.mean(rr))))
        print(rows[-1], flush=True)

lines = [f"# Eval sonuçları ({len(questions)} soru, hit@{K} ve MRR)\n",
         f"| Model | Chunk boyutu | Parça sayısı | hit@{K} | MRR |", "|---|---|---|---|---|"]
lines += [f"| {m} | {s} | {n} | {h:.2f} | {r:.3f} |" for m, s, n, h, r in rows]
(HERE / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
