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
    from src.rewriter import analyze
except Exception:
    analyze = None
try:
    from src.rewriter import condense
except Exception:
    condense = None
try:
    from src.router import normalize, route
    route("test", True)
except Exception as e:
    route = None
    print(f"[uyarı] route(question, has_history) kullanılamıyor ({e!r})")
MODE = "analyze" if analyze else "route+condense (yedek; analyze: pending)"
print(f"[bilgi] mod: {MODE}")

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


INTENTS = ["notes", "followup", "sources", "meta"]
conf = {e: {p: 0 for p in INTENTS} for e in INTENTS}
kw_ok = kw_n = 0
raw_ranks, rew_ranks, lat = [], [], []


def decide(q, history):
    """-> (intent, query) ; analyze varsa onu, yoksa route + condense yedeği."""
    if analyze:
        r = analyze(q, history)
        return r["intent"], r.get("query") or q
    intent = route(q, True) if route else "notes"
    cq = q
    if intent == "notes" and condense:
        try:
            cq = condense(q, history)
        except Exception:
            cq = q
    return intent, cq


for conv in convs:
    history = []
    for i, t in enumerate(conv["turns"]):
        q, exp = t["question"], t["expected_intent"]
        if i > 0:  # ilk tur geçmişsiz
            t0 = time.perf_counter()
            intent, aq = decide(q, history)
            lat.append(time.perf_counter() - t0)
            conf[exp][intent if intent in INTENTS else "notes"] += 1
            if exp == "notes":
                if t.get("query_keyword"):
                    kw_n += 1
                    kw_ok += normalize(t["query_keyword"]) in normalize(aq)  # Python lower() "İ"yi bozar
                if t["expected_source"]:
                    raw_ranks.append(rank_of(q, t["expected_source"]))
                    rew_ranks.append(rank_of(aq, t["expected_source"]))
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": t["reference_answer"]}]

fmt = lambda m: f"{m[0]:.2f} | {m[1]:.3f}" if m else "- | -"
raw, rew = metrics(raw_ranks), metrics(rew_ranks)
tot = sum(sum(r.values()) for r in conf.values())
ok = sum(conf[e][e] for e in INTENTS)
lines = [f"# Takip sorusu eval ({len(convs)} konuşma, {tot} geçmişli tur)\n",
         f"Mod: **{MODE}**\n",
         f"- Intent doğruluğu (genel): {ok}/{tot} = {ok / tot:.2f}", ""]
lines += ["| Beklenen \\ Tahmin | " + " | ".join(INTENTS) + " | doğruluk |", "|---|" + "---|" * (len(INTENTS) + 1)]
for e in INTENTS:
    n = sum(conf[e].values())
    lines.append(f"| {e} | " + " | ".join(str(conf[e][p]) for p in INTENTS) + f" | {conf[e][e]}/{n} = {conf[e][e] / n:.2f} |" if n else f"| {e} | - | - | - | - | - |")
lines += ["", f"- Sorgu niyet korunumu (anahtar kelime): {kw_ok}/{kw_n} = {kw_ok / kw_n:.2f}" if kw_n else "- Sorgu niyet korunumu: -",
          "", f"Geri getirme ({len(raw_ranks)} notes turu):", "", "| Sorgu | hit@3 | MRR |", "|---|---|---|",
          f"| Ham soru | {fmt(raw)} |", f"| Analiz sorgusu | {fmt(rew)} |", "",
          f"- Ort. gecikme (karar+yoğunlaştırma): {sum(lat) / len(lat):.3f} sn"]
if not analyze:
    lines.append("- analyze: pending (src.rewriter.analyze henüz yok; route(q, True) + condense ile ölçüldü, route 'sources' üretemez)")
out = "\n".join(lines) + "\n"
(HERE / "followup_results.md").write_text(out, encoding="utf-8")
print(out)
