"""Varlık koruması ölçümü: gerçek arama + gerçek LLM ile services.ask (geçmiş boş).
Çalıştır:  uv run python -m eval.run_entity_eval --guard off|on --out /tmp/x.json
Kümeler: threshold_questions.json + threshold_frozen.json (answerable, near-miss, entity-swap).
Kullanıcı ayarına/sohbetlerine dokunmaz: set_override(örnek notlar), XDG dizinleri geçici olmalı.
Sezgi: cevaplanamaz soruda cevap "Bu bilgi notlarda yok" değilse YANLIŞ cevap sayılır; cevaplanabilirde ret = yanlış ret."""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "10")
HERE = Path(__file__).parent
CATS = ("answerable", "near-miss", "entity-swap")


def refused(text: str) -> bool:
    return "notlarda yok" in text.lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guard", choices=["on", "off"], required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from desktop import services
    from src import config, settings
    from src.pipeline import build_index
    settings.set_override(config.NOTES_DIR)
    build_index()
    config.ENTITY_GUARD_ENABLED = a.guard == "on"
    items = [i for f in ("threshold_questions.json", "threshold_frozen.json")
             for i in json.loads((HERE / f).read_text("utf-8")) if i["category"] in CATS]
    rows = []
    for it in items:
        ans, res, info = services.ask(it["q"], config.TOP_K, config.INDEX_BACKEND, prior_messages=[])
        rows.append(dict(id=it["id"], q=it["q"], cat=it["category"], answerable=it["answerable"],
                         refused=refused(ans), entity_missing=info.get("entity_missing"),
                         below=bool(info.get("below_threshold")), answer=ans[:300]))
        print(rows[-1]["cat"], rows[-1]["refused"], rows[-1]["entity_missing"], it["q"], flush=True)
    Path(a.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), "utf-8")


if __name__ == "__main__":
    main()
