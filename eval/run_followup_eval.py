"""Takip sorusu (konuşma hafızası) değerlendirmesi: sadece yönlendirme + geri getirme, cevap üretimi yok.
Çalıştır:  uv run python -m eval.run_followup_eval
(a) route doğruluğu, (b) hit@3 / MRR: ham soru vs yoğunlaştırılmış soru, (c) ort. condense gecikmesi.
src.rewriter / route(has_history) yoksa uyarı basılır, ham soru baz çizgisi yine çalışır."""
import json
import time
from pathlib import Path

K = 3
HERE = Path(__file__).parent
convs = json.loads((HERE / "followup_questions.json").read_text("utf-8"))

try:
    from src.router import route
    route("test", True)
except Exception as e:  # eksik modül veya eski imza
    route = None
    print(f"[uyarı] route(question, has_history) kullanılamıyor ({e!r}); route doğruluğu atlandı.")
try:
    from src.rewriter import condense
except Exception as e:
    condense = None
    print(f"[uyarı] src.rewriter.condense yok ({e!r}); rewrite sütunları 'pending'.")

from src import config, settings
from src.pipeline import build_index

settings.set_override(config.NOTES_DIR)  # kullanıcı ayarından bağımsız: örnek notlar
from src.retriever import retrieve

build_index()  # indeks yoksa kurar, varsa yeniden kullanır


def rank_of(q, source):
    r = next((i for i, (c, _) in enumerate(retrieve(q, 10), 1) if c.source == source), None)
    return r


def metrics(ranks):
    n = len(ranks)
    if not n:
        return None
    return sum(r is not None and r <= K for r in ranks) / n, sum(1 / r if r else 0 for r in ranks) / n


route_ok = route_n = 0
raw_ranks, rew_ranks, lat = [], [], []
for conv in convs:
    history = []
    for i, t in enumerate(conv["turns"]):
        q = t["question"]
        if route and i > 0:  # ilk tur geçmişsiz; takip turları has_history=True
            route_n += 1
            route_ok += route(q, True) == t["expected_route"]
        if i > 0 and t["expected_route"] != "meta" and t["expected_source"]:
            raw_ranks.append(rank_of(q, t["expected_source"]))
            if condense:
                t0 = time.perf_counter()
                cq = condense(q, history)
                lat.append(time.perf_counter() - t0)
                rew_ranks.append(rank_of(cq, t["expected_source"]))
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": t["reference_answer"]}]

fmt = lambda m: f"{m[0]:.2f} | {m[1]:.3f}" if m else "pending | pending"
raw = metrics(raw_ranks)
rew = metrics(rew_ranks) if condense else None
lines = [f"# Takip sorusu eval ({len(convs)} konuşma, {len(raw_ranks)} geri getirme turu)\n",
         "| Yöntem | hit@3 | MRR |", "|---|---|---|",
         f"| Ham soru (baseline) | {fmt(raw)} |",
         f"| Yoğunlaştırılmış (rewrite) | {fmt(rew)} |", ""]
lines.append(f"- Route doğruluğu: " + (f"{route_ok}/{route_n} = {route_ok / route_n:.2f}" if route and route_n else "pending (route has_history yok)"))
lines.append("- Ort. condense gecikmesi: " + (f"{sum(lat) / len(lat):.2f} sn" if lat else "pending"))
if not condense:
    lines.append("- rewrite: pending (src.rewriter henüz yok)")
out = "\n".join(lines) + "\n"
(HERE / "followup_results.md").write_text(out, encoding="utf-8")
print(out)
