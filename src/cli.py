"""Komutlar:  uv run python -m src.cli index   |   uv run python -m src.cli ask "soru"   |   ... chat """
import argparse

from . import config, settings
from .chunker import chunk_label
from .generator import answer, answer_meta
from .pipeline import build_index
from .retriever import retrieve
from .router import route


def _apply_dir(args):
    d = getattr(args, "notes_dir", None)
    if d:
        try:
            settings.set_override(settings.validate_dir(d))
        except ValueError as e:
            raise SystemExit(f"Hata: {e}")


def cmd_set_notes_dir(args):
    try:
        p = settings.set_notes_dir(args.path)
    except ValueError as e:
        raise SystemExit(f"Hata: {e}")
    print(f"Not klasörü ayarlandı: {p}")


def cmd_index(args):
    _apply_dir(args)
    try:
        res = build_index()       # 1. yükle 2. parçala 3. embed 4. indeksle (iki yöntem de)
    except ValueError as e:
        raise SystemExit(str(e))
    print(f"{res.summary()} ({config.EMBED_MODEL}).")


def cmd_ask(args):
    _apply_dir(args)
    if route(args.question) == "meta":                     # 0. yönlendir: aramaya gerek yok
        print("Cevap:\n" + answer_meta(args.question))
        return
    results = retrieve(args.question, backend=args.backend)           # 5. geri getir
    print("Kaynak parçalar:")
    for c, s in results:
        print(f"  - {c.id} ({chunk_label(c)}) skor={s:.3f}")
    print("\nCevap:\n" + answer(args.question, results))               # 6. üret


def cmd_chat(args):
    """Sohbet REPL: geçmiş sadece bellekte tutulur (kaydedilmez). Çıkış: boş satır, 'q' veya Ctrl-D."""
    from . import history as hist
    from .conversation import fit_budget, window
    from .generator import answer_followup
    from .rewriter import analyze
    from .sources import answer_sources, cited_indices
    _apply_dir(args)
    msgs: list[dict] = []
    print("Sohbet başladı. Çıkmak için boş satır veya 'q'.")
    while True:
        try:
            q = input("\nSoru> ").strip()
        except EOFError:
            break
        if not q or q.lower() in ("q", "quit", "exit"):
            break
        h = window(msgs)
        a = analyze(q, h)
        intent, query = a["intent"], a.get("query") or q
        prev_msg = next((m for m in reversed(msgs) if m["role"] == "assistant"), {})
        prev = prev_msg.get("sources") or []
        if intent in ("followup", "sources") and not prev:   # dayanacak kaynak yok: normal arama
            intent = "notes"
        print(f"[niyet: {intent}]" + (f" [aranan: {query}]" if query != q else ""))
        results = []
        if intent == "meta":
            ans = answer_meta(q)
        elif intent == "sources":
            ans = answer_sources(prev_msg.get("text", ""), prev, q)
            idxs = cited_indices(prev_msg.get("text", ""), len(prev))
            kept = [prev[i - 1] for i in idxs] if idxs else prev
            print("Cevap:\n" + ans)
            msgs += [{"role": "user", "text": q, "sources": []},
                     {"role": "assistant", "text": ans, "sources": kept}]
            continue
        elif intent == "followup":
            ans = answer_followup(q, h, prev)
            print("Cevap:\n" + ans)
            msgs += [{"role": "user", "text": q, "sources": []},
                     {"role": "assistant", "text": ans, "sources": prev}]
            continue
        else:
            results = retrieve(query, backend=args.backend)
            h, results = fit_budget(h, results, q)
            ans = answer(q, results, h)
            for c, s in results:
                print(f"  - {c.id} ({chunk_label(c)}) skor={s:.3f}")
        print("Cevap:\n" + ans)
        m = {"role": "assistant", "text": ans, "sources": hist.sources_from_results(results)}
        if query != q and intent == "notes":
            m["query"] = query
        msgs += [{"role": "user", "text": q, "sources": []}, m]


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(required=True)
    ix = sub.add_parser("index")
    ix.add_argument("--notes-dir", help="bu çalıştırma için not klasörü (ayarı değiştirmez)")
    ix.set_defaults(fn=cmd_index)
    sd = sub.add_parser("set-notes-dir", help="kalıcı not klasörünü ayarla")
    sd.add_argument("path")
    sd.set_defaults(fn=cmd_set_notes_dir)
    a = sub.add_parser("ask")
    a.add_argument("question")
    a.add_argument("--notes-dir", help="bu çalıştırma için not klasörü (ayarı değiştirmez)")
    a.add_argument("--backend", default=config.INDEX_BACKEND, choices=["numpy", "chroma"])
    a.set_defaults(fn=cmd_ask)
    c = sub.add_parser("chat", help="çok turlu sohbet (geçmiş bellekte)")
    c.add_argument("--notes-dir", help="bu çalıştırma için not klasörü (ayarı değiştirmez)")
    c.add_argument("--backend", default=config.INDEX_BACKEND, choices=["numpy", "chroma"])
    c.set_defaults(fn=cmd_chat)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
