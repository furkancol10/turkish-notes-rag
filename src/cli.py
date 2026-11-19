"""Komutlar:  uv run python -m src.cli index   |   uv run python -m src.cli ask "soru"   |   ... chat """
import argparse

from . import config, qa, settings
from .chunker import chunk_label
from .pipeline import build_index


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


def _threshold(args):
    """Etkin eşik (None = kapalı): --no-threshold > --threshold > kayıtlı ayar."""
    if getattr(args, "no_threshold", False):
        return None
    if getattr(args, "threshold", None) is not None:
        return args.threshold
    return settings.get_score_threshold() if settings.get_threshold_enabled() else None


def _qa_kwargs(args):
    th = _threshold(args)
    return dict(top_k=config.TOP_K, backend=args.backend, threshold=th, threshold_enabled=th is not None)


def _ask(question, args, prior=None):
    try:
        return qa.ask(question, prior_messages=prior or [], **_qa_kwargs(args))
    except qa.AskError as e:
        raise SystemExit(str(e))


def _print_sources(results):
    for c, s in results:
        if hasattr(c, "id"):
            print(f"  - {c.id} ({chunk_label(c)}) skor={s:.3f}")


def _print_answer(ans, info):
    """Eşik/varlık koruması reddinde açıklayıcı notu da yazar."""
    print("Cevap:\n" + ans + ("\n" + info["note"] if info.get("note") else ""))


def cmd_ask(args):
    _apply_dir(args)
    ans, results, info = _ask(args.question, args)       # tek turlu: geçmiş yok
    if results:
        print("Kaynak parçalar:")
        _print_sources(results)
        print()
    _print_answer(ans, info)


def cmd_chat(args):
    """Sohbet REPL: geçmiş sadece bellekte tutulur (kaydedilmez). Çıkış: boş satır, 'q' veya Ctrl-D."""
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
        ans, results, info = _ask(q, args, msgs)
        print(f"[niyet: {info['intent']}]" + (f" [aranan: {info['query']}]" if info.get("query") else ""))
        if info["intent"] == "notes":
            _print_sources(results)
        _print_answer(ans, info)
        msgs += [{"role": "user", "text": q, "sources": []}, qa.assistant_message(q, ans, results, info)]


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
    a.add_argument("--threshold", type=float, help="skor eşiği (ayarı değiştirmez)")
    a.add_argument("--no-threshold", action="store_true", help="eşiği kapat")
    a.set_defaults(fn=cmd_ask)
    c = sub.add_parser("chat", help="çok turlu sohbet (geçmiş bellekte)")
    c.add_argument("--notes-dir", help="bu çalıştırma için not klasörü (ayarı değiştirmez)")
    c.add_argument("--backend", default=config.INDEX_BACKEND, choices=["numpy", "chroma"])
    c.add_argument("--threshold", type=float, help="skor eşiği (ayarı değiştirmez)")
    c.add_argument("--no-threshold", action="store_true", help="eşiği kapat")
    c.set_defaults(fn=cmd_chat)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
