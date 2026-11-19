"""Komutlar:  uv run python -m src.cli index   |   uv run python -m src.cli ask "soru" """
import argparse

from . import config
from .chunker import chunk_docs
from .embedder import embed_passages
from .generator import answer, answer_meta
from .index import get_index, index_name
from .loader import load_notes
from .retriever import retrieve
from .router import route


def cmd_index(args):
    docs = load_notes()                                   # 1. yükle
    chunks = chunk_docs(docs)                             # 2. parçala
    vecs = embed_passages([c.text for c in chunks])       # 3. embed
    name = index_name(config.EMBED_MODEL, config.CHUNK_STRATEGY, config.CHUNK_SIZE)
    for backend in ("numpy", "chroma"):                   # 4. indeksle (iki yöntem de)
        get_index(backend, name).build(chunks, vecs)
    print(f"{len(docs)} not -> {len(chunks)} parça indekslendi ({config.EMBED_MODEL}).")


def cmd_ask(args):
    if route(args.question) == "meta":                     # 0. yönlendir: aramaya gerek yok
        print("Cevap:\n" + answer_meta(args.question))
        return
    results = retrieve(args.question, backend=args.backend)           # 5. geri getir
    print("Kaynak parçalar:")
    for c, s in results:
        print(f"  - {c.id} ({c.heading}) skor={s:.3f}")
    print("\nCevap:\n" + answer(args.question, results))               # 6. üret


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(required=True)
    sub.add_parser("index").set_defaults(fn=cmd_index)
    a = sub.add_parser("ask")
    a.add_argument("question")
    a.add_argument("--backend", default=config.INDEX_BACKEND, choices=["numpy", "chroma"])
    a.set_defaults(fn=cmd_ask)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
