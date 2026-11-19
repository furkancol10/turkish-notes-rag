"""Komutlar:  uv run python -m src.cli index   |   uv run python -m src.cli ask "soru" """
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
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
