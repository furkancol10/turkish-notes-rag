"""v2 ölçümü (tek seferlik, dondurulmuş setler). uv run python -m eval.run_filter_eval_v2
Hit: filtre boş değil, beklenen belgelerin tümünü içerir ve en fazla 1 fazla belge."""
import json, os, tempfile
from pathlib import Path
HERE = Path(__file__).parent
def load(n):
    d = json.loads((HERE / n).read_text("utf-8")); assert d["frozen"] is True; return d["questions"]
def main():
    tmp = tempfile.mkdtemp(prefix="filter_v2_"); os.environ["XDG_CONFIG_HOME"] = tmp
    from src import config, settings
    from src.pipeline import build_index
    from src.retriever import retrieve_with_info
    config.INDEX_DIR = Path(tmp) / "index"; settings.set_override(config.NOTES_DIR); build_index()
    f = lambda q: retrieve_with_info(q, 5, backend=config.INDEX_BACKEND, doc_filter="auto")[1]["filter"]
    st = lambda s: Path(s).stem
    G, T = load("general_frozen_v2.json"), load("doc_targeted_v2.json")
    wrong = [(g["q"], r) for g in G if (r := f(g["q"]))]
    hit, none, wrongdoc = 0, [], []
    for t in T:
        r = f(t["q"]); got = {st(x) for x in (r or [])}; exp = set(t["docs"])
        if not got: none.append(t["q"])
        elif exp <= got and len(got - exp) <= 1: hit += 1
        else: wrongdoc.append((t["q"], sorted(got)))
    L = ["# Filtre v2 sonuçları (tek ölçüm, dondurulmuş setler)", "",
     "Setler: `eval/general_frozen_v2.json`, `eval/doc_targeted_v2.json` (kurallar bu sete göre ayarlanmaz).", "",
     "Hit tanımı: filtre boş değil, beklenen belgelerin tümünü içerir ve en fazla 1 fazla belge içerir.", "",
     f"- Genel sorularda yanlış filtre: **{len(wrong)}/{len(G)}** (hedef 0)",
     f"- Hedefli isabet: **{hit}/{len(T)}** ({100*hit/len(T):.0f}%)",
     f"- Hedefli kaçırılan (None): {len(none)}; yanlış belge: {len(wrongdoc)}", ""]
    if wrong: L += ["Yanlış filtre alan genel sorular:"] + [f"- {q} -> {r}" for q, r in wrong] + [""]
    if none: L += ["Kaçırılan (None):"] + [f"- {q}" for q in none] + [""]
    if wrongdoc: L += ["Yanlış belge:"] + [f"- {q} -> {r}" for q, r in wrongdoc] + [""]
    (HERE / "filter_v2_results.md").write_text("\n".join(L), "utf-8"); print("\n".join(L))
main()
