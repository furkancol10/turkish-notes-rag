"""Belgeler arası KARIŞMA değerlendirmesi.
Çalıştır:  uv run python -m eval.run_mixing_eval [--no-generate] [--corpus notes|docs] [--k 10] [--out eval/mixing_results.md]
Metrikler: arama saflığı (top-k parçanın izinli belgelerden payı), cevap kirlenmesi (atıf yapılan kaynaklardan
izinli olmayanların payı), >=1 yabancı atıflı cevap %, anahtar bilgi (key_fact) kapsaması.
Sadece public API: src.retriever.retrieve(q, k, backend), src.generator.answer(q, results)."""
import argparse
import json
import re
import tempfile
import unicodedata
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
DOCS_DIR = ROOT.parent / "Katalog" / "Docs"   # salt okunur


def fold(s: str) -> str:
    s = s.replace("İ", "i").replace("I", "ı").lower().replace("ı", "i")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def stem(name: str) -> str:
    return Path(name).stem


def allowed_stems(item) -> set[str]:
    return {stem(d) for d in item["allowed_docs"]}


def purity(sources: list[str], allowed: set[str]) -> float:
    return sum(stem(s) in allowed for s in sources) / len(sources) if sources else 0.0


def cited_sources(text: str, results) -> list[str]:
    nums = {int(n) for grp in re.findall(r"\[([\d,\s]+)\]", text) for n in re.findall(r"\d+", grp)}
    return [results[n - 1][0].source for n in sorted(nums) if 1 <= n <= len(results)]


def keyfact_recall(text: str, facts: list[str]):
    if not facts:
        return None
    t = fold(text)
    return sum(fold(f) in t for f in facts) / len(facts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-generate", action="store_true")
    ap.add_argument("--corpus", choices=["notes", "docs"])
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--out", default=str(HERE / "mixing_results.md"))
    a = ap.parse_args()
    items = json.loads((HERE / "mixing_questions.json").read_text("utf-8"))

    import os
    tmp = tempfile.mkdtemp(prefix="mixing_eval_")
    os.environ["XDG_CONFIG_HOME"] = tmp
    from src import config, settings
    from src.pipeline import build_index
    from src.retriever import retrieve
    config.INDEX_DIR = Path(tmp) / "index"   # gerçek indeksi bozma
    gen = None
    if not a.no_generate:
        from src.generator import answer as gen

    rows = []
    for corpus, folder in (("notes", config.NOTES_DIR), ("docs", DOCS_DIR)):
        if a.corpus and a.corpus != corpus:
            continue
        settings.set_override(folder)
        print(f"[{corpus}] indeks kuruluyor: {build_index().summary()}", flush=True)
        for it in (i for i in items if i["corpus"] == corpus):
            allowed = allowed_stems(it)
            res = retrieve(it["question"], a.k, backend=config.INDEX_BACKEND)
            srcs = [c.source for c, _ in res]
            r = {"it": it, "purity": purity(srcs, allowed), "top": srcs}
            if gen:
                ans = gen(it["question"], res)
                cs = cited_sources(ans, res)
                r.update(ans=ans, cited=cs, contam=(1 - purity(cs, allowed)) if cs else 0.0,
                         foreign=any(stem(s) not in allowed for s in cs),
                         recall=None if it["comparison"] else keyfact_recall(ans, it["key_facts"]))
            rows.append(r)
            print(f"  purity={r['purity']:.2f} {'foreign ' if r.get('foreign') else ''}{it['question']}", flush=True)
    write_report(rows, a)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def write_report(rows, a):
    L = ["# Belgeler arası karışma değerlendirmesi", "",
         f"k={a.k}; üretim: {'kapalı' if a.no_generate else 'açık'}. "
         "Saflık = top-k parçanın izinli belgelerden payı; kirlenme = atıf yapılan kaynaklardan izinli olmayanların payı; "
         "yabancı atıflı = en az 1 izinsiz belgeye atıf yapan cevap oranı; anahtar bilgi = beklenen anahtar kelimelerin kapsaması "
         "(sadece tek belgelik sorular).", "",
         "| Korpus | Tür | N | Arama saflığı | Kirlenme | Yabancı atıflı cevap | Anahtar bilgi |", "|---|---|---|---|---|---|---|"]
    for corpus in ("notes", "docs"):
        for kind, flag in (("tek belge", False), ("karşılaştırma", True), ("tümü", None)):
            rs = [r for r in rows if r["it"]["corpus"] == corpus and (flag is None or r["it"]["comparison"] == flag)]
            if not rs:
                continue
            g = "ans" in rs[0]
            f = lambda v: "-" if v != v else f"{100 * v:.0f}%"
            L.append(f"| {corpus} | {kind} | {len(rs)} | {f(mean(r['purity'] for r in rs))} | "
                     f"{f(mean(r['contam'] for r in rs)) if g else '-'} | "
                     f"{f(mean(float(r['foreign']) for r in rs)) if g else '-'} | "
                     f"{f(mean(r['recall'] for r in rs)) if g else '-'} |")
    if rows and "ans" in rows[0]:
        bad = sorted((r for r in rows if r["foreign"]), key=lambda r: -r["contam"])[:5]
        L += ["", "## En kötü 5 örnek (yabancı atıflı)", ""]
        for r in bad:
            L += [f"- **{r['it']['question']}** ({r['it']['corpus']}; izinli: {', '.join(r['it']['allowed_docs'])}; "
                  f"kirlenme {100 * r['contam']:.0f}%)", f"  - atıflar: {', '.join(r['cited'])}",
                  f"  - cevap: {r['ans'][:300].replace(chr(10), ' ')}"]
        if not bad:
            L.append("Yabancı atıflı cevap yok.")
    else:
        L += ["", "## En düşük saflıklı 5 soru", ""]
        for r in sorted(rows, key=lambda r: r["purity"])[:5]:
            L.append(f"- {r['it']['question']} ({r['purity']:.2f}); top: {', '.join(r['top'][:5])}")
    Path(a.out).write_text("\n".join(L) + "\n", "utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
