"""Belge filtresi ölçümü (yalnız arama, LLM yok): retriever.retrieve_with_info public API.
Çalıştır:  uv run python -m eval.run_filter_eval [--no-write]
 - isabet: mixing_questions.json (notes) sorularında filtre boş değil ve izinli belgelerin içinde
 - yanlış filtre: general_frozen.json (DONDURULMUŞ) sorularında filtre dolu (hedef 0)
Sonucu eval/mixing_results.md'ye 'Genel soru seti (dondurulmuş)' bölümü olarak yazar/günceller."""
import argparse
import json
import os
import re
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SECTION = "## Genel soru seti (dondurulmuş)"


def stem(s: str) -> str:
    return Path(s).stem


def load_general() -> list[dict]:
    d = json.loads((HERE / "general_frozen.json").read_text("utf-8"))
    assert d.get("frozen") is True
    return d["questions"]


def score(items, general, filt):
    """filt(q) -> list[source]|None. -> (hit_rate, wrong_rate, hits_detail, wrong_detail)"""
    tgt = [i for i in items if i["corpus"] == "notes"]
    hit, miss = [], []
    for i in tgt:
        f = filt(i["question"])
        ok = bool(f) and {stem(s) for s in f} <= {stem(d) for d in i["allowed_docs"]}
        (hit if ok else miss).append((i["question"], f))
    wrong = [(g["q"], f) for g in general if (f := filt(g["q"]))]
    return len(hit) / len(tgt), len(wrong) / len(general), miss, wrong


def render(n_t, hr, n_g, wr, miss, wrong, ref) -> str:
    L = [SECTION, "", f"Belirli belgeye işaret eden sorularda filtre isabeti: **{100 * hr:.0f}%** (N={n_t}, notes). "
         f"Genel sorularda yanlış filtre oranı: **{100 * wr:.0f}%** ({len(wrong)}/{n_g}; hedef 0%). Ölçüm: {ref}.",
         "", "Set: `eval/general_frozen.json` (dondurulmuş, kurallar bu sete göre ayarlanmaz). Yalnız arama, LLM yok.", ""]
    if wrong:
        L += ["Yanlış filtre alan genel sorular:", ""] + [f"- {q} -> {', '.join(f)}" for q, f in wrong] + [""]
    if miss:
        L += ["Filtre isabetsiz belge soruları:", ""] + [f"- {q} -> {f}" for q, f in miss] + [""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="", help="ölçümün hangi kod durumunda yapıldığı (etiket)")
    ap.add_argument("--out", default=str(HERE / "mixing_results.md"))
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="filter_eval_")
    os.environ["XDG_CONFIG_HOME"] = tmp
    from src import config, settings
    from src.pipeline import build_index
    from src.retriever import retrieve_with_info
    config.INDEX_DIR = Path(tmp) / "index"
    settings.set_override(config.NOTES_DIR)
    print(build_index().summary(), flush=True)
    items = json.loads((HERE / "mixing_questions.json").read_text("utf-8"))
    general = load_general()
    filt = lambda q: retrieve_with_info(q, 5, backend=config.INDEX_BACKEND, doc_filter="auto")[1]["filter"]
    hr, wr, miss, wrong = score(items, general, filt)
    txt = render(sum(i["corpus"] == "notes" for i in items), hr, len(general), wr, miss, wrong, a.ref or "çalışma ağacı")
    print(txt)
    if not a.no_write:
        p = Path(a.out)
        old = p.read_text("utf-8") if p.exists() else ""
        old = re.split(rf"\n?{re.escape(SECTION)}", old)[0].rstrip("\n")
        p.write_text(old + "\n\n" + txt + "\n", "utf-8")


if __name__ == "__main__":
    main()
