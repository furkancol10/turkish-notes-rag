"""Skor eşiği kalibrasyonu: top-1 skoru < eşik ise uygulama "Bu bilgi notlarda yok" der.
Çalıştır:  uv run python -m eval.run_threshold_eval   (eval/threshold_results.md yazar)
Eşik SADECE tuning kümesinde (threshold_questions.json) seçilir; dondurulmuş küme (threshold_frozen.json)
seçimden sonra bir kez değerlendirilir. Kural: yanlış-ret <= %5, sonra en çok doğru-ret.
Kullanıcı ayarına dokunmaz (set_override); CPU 6 iş parçacığıyla sınırlı."""
import os
os.environ.setdefault("OMP_NUM_THREADS", "6")
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

torch.set_num_threads(6)
HERE = Path(__file__).parent
BACKENDS = ("chroma", "numpy")
MAX_FALSE_REFUSAL = 0.05
GRID = [round(0.30 + 0.01 * i, 2) for i in range(51)]


def load(name):
    return json.loads((HERE / name).read_text("utf-8"))


def score_all(items, retrieve):
    out = {}
    for it in items:
        r = retrieve(it["q"], 2)
        s1, s2 = r[0][1], (r[1][1] if len(r) > 1 else 0.0)
        out[it["id"]] = dict(top1=s1, margin=s1 - s2, src=r[0][0].source)
    return out


def rates(items, sc, t):
    """Eşik t: top1 < t -> ret."""
    ans = [i for i in items if i["answerable"]]
    un = [i for i in items if not i["answerable"]]
    fr = sum(sc[i["id"]]["top1"] < t for i in ans) / max(len(ans), 1)
    cr = sum(sc[i["id"]]["top1"] < t for i in un) / max(len(un), 1)
    tp = cr * len(un)                      # doğru ret
    fp = fr * len(ans)                     # yanlış ret
    prec = tp / (tp + fp) if tp + fp else 0.0
    f1 = 2 * prec * cr / (prec + cr) if prec + cr else 0.0
    return dict(t=t, false_ref=fr, correct_ref=cr, bal_acc=(cr + 1 - fr) / 2, f1=f1)


def choose(items, sc):
    sweep = [rates(items, sc, t) for t in GRID]
    ok = [r for r in sweep if r["false_ref"] <= MAX_FALSE_REFUSAL]
    best = max(ok, key=lambda r: (r["correct_ref"], r["t"]))  # eşit ret oranında en yüksek eşik
    return sweep, best


def hist(items, sc, edges):
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        a = sum(lo <= sc[i["id"]]["top1"] < hi for i in items if i["answerable"])
        u = sum(lo <= sc[i["id"]]["top1"] < hi for i in items if not i["answerable"])
        rows.append((lo, hi, a, u))
    return rows


def pct(x):
    return f"{100 * x:.1f}%"


def percat(items, sc, t):
    d = defaultdict(lambda: [0, 0])
    for i in items:
        d[i["category"]][0] += sc[i["id"]]["top1"] < t
        d[i["category"]][1] += 1
    return d


def main():
    from src import config, settings
    from src.pipeline import build_index
    settings.set_override(config.NOTES_DIR)
    build_index()
    from src.retriever import retrieve
    tune, frozen = load("threshold_questions.json"), load("threshold_frozen.json")
    S = {}
    for b in BACKENDS:
        f = lambda q, k, b=b: retrieve(q, k, backend=b)
        S[b] = (score_all(tune, f), score_all(frozen, f))
    lines = ["# Skor eşiği kalibrasyonu (bge-m3, kosinüs)", "",
             f"Tuning: {len(tune)} soru, dondurulmuş: {len(frozen)} soru. Kural: yanlış-ret <= %{MAX_FALSE_REFUSAL*100:.0f}, "
             "sonra en çok doğru-ret (eşit ise yüksek eşik). Ret = top-1 skoru < eşik.", ""]
    # arka uç ölçek karşılaştırması
    allids = [i["id"] for i in tune + frozen]
    sc_c = {**S["chroma"][0], **S["chroma"][1]}
    sc_n = {**S["numpy"][0], **S["numpy"][1]}
    diff = max(abs(sc_c[i]["top1"] - sc_n[i]["top1"]) for i in allids)
    same_src = sum(sc_c[i]["src"] == sc_n[i]["src"] for i in allids)
    lines += ["## Arka uç ölçeği", f"Chroma vs numpy top-1 skor farkı: maks {diff:.5f}; aynı top-1 kaynak: {same_src}/{len(allids)}. "
              + ("Aynı ölçek (kosinüs)." if diff < 0.01 else "ÖLÇEK FARKLI, ayrı eşik gerekebilir."), ""]
    chosen = {}
    for b in BACKENDS:
        st, sf = S[b]
        sweep, best = choose(tune, st)
        T = best["t"]
        chosen[b] = T
        fz = rates(frozen, sf, T)
        edges = [0.30, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 1.01]
        lines += [f"## Arka uç: {b}", "", "### Top-1 skor histogramı (tuning)", "",
                  "| Aralık | Cevaplanabilir | Cevaplanamaz |", "|---|---|---|"]
        for lo, hi, a, u in hist(tune, st, edges):
            lines.append(f"| [{lo:.2f}, {min(hi,1.0):.2f}) | {a} | {u} |")
        lines += ["", "### Süpürme özeti (tuning, her 0.05)", "",
                  "| Eşik | Yanlış-ret | Doğru-ret | Dengeli doğruluk | F1 (ret) |", "|---|---|---|---|---|"]
        for r in sweep:
            if round(r["t"] * 100) % 5 == 0 or r["t"] == T:
                lines.append(f"| {r['t']:.2f}{' **seçilen**' if r['t']==T else ''} | {pct(r['false_ref'])} | {pct(r['correct_ref'])} | {pct(r['bal_acc'])} | {r['f1']:.3f} |")
        bb = max(sweep, key=lambda r: r["bal_acc"])
        lines += ["", f"Tuning dengeli doğruluğu en yüksek eşik: {bb['t']:.2f} ({pct(bb['bal_acc'])}, yanlış-ret {pct(bb['false_ref'])}) - bilgi amaçlı.", "",
                  f"### Seçilen eşik: **{T:.2f}**", "",
                  "| Küme | Yanlış-ret | Doğru-ret | Dengeli doğruluk | F1 |", "|---|---|---|---|---|",
                  f"| tuning | {pct(best['false_ref'])} | {pct(best['correct_ref'])} | {pct(best['bal_acc'])} | {best['f1']:.3f} |",
                  f"| dondurulmuş (tek değerlendirme) | {pct(fz['false_ref'])} | {pct(fz['correct_ref'])} | {pct(fz['bal_acc'])} | {fz['f1']:.3f} |", "",
                  "### Kategori bazında ret oranı (eşik " + f"{T:.2f})", "", "| Kategori | tuning | dondurulmuş |", "|---|---|---|"]
        pt, pf = percat(tune, st, T), percat(frozen, sf, T)
        for c in ("answerable", "off-topic", "near-miss", "entity-swap"):
            lab = "cevaplanabilir (yanlış ret)" if c == "answerable" else c
            lines.append(f"| {lab} | {pt[c][0]}/{pt[c][1]} | {pf[c][0]}/{pf[c][1]} |")
        # marj
        ma = np.mean([st[i["id"]]["margin"] for i in tune if i["answerable"]])
        mu = np.mean([st[i["id"]]["margin"] for i in tune if not i["answerable"]])
        ta = np.mean([st[i["id"]]["top1"] for i in tune if i["answerable"]])
        tu = np.mean([st[i["id"]]["top1"] for i in tune if not i["answerable"]])
        lines += ["", f"Ortalama top-1: cevaplanabilir {ta:.3f}, cevaplanamaz {tu:.3f}. Ortalama top1-top2 marjı: cevaplanabilir {ma:.4f}, cevaplanamaz {mu:.4f}.", ""]
        # kaçırılan cevaplanamazlar (dondurulmuşta eşiği geçen) ve yanlış retler
        miss = [i for i in frozen if not i["answerable"] and sf[i["id"]]["top1"] >= T]
        fal = [i for i in frozen if i["answerable"] and sf[i["id"]]["top1"] < T]
        lines += ["Dondurulmuşta yanlış cevaplanacak (ret edilemeyen) sorular:", ""] + [f"- ({i['category']}, {sf[i['id']]['top1']:.3f}) {i['q']}" for i in miss]
        lines += ["", "Dondurulmuşta yanlış ret edilen sorular:", ""] + [f"- ({sf[i['id']]['top1']:.3f}) {i['q']}" for i in fal] + [""]
    (HERE / "threshold_results.md").write_text("\n".join(lines), "utf-8")
    print("\n".join(lines[:12]))
    print("chosen", chosen)


if __name__ == "__main__":
    main()
