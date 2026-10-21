"""Create the pgvector extension, tables and indexes, then load the knowledge base.

Usage (from backend/):  python -m scripts.init_db [--reembed]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal, init_db  # noqa: E402
from app.services.embeddings import get_embedder  # noqa: E402
from app.services.ingest import ingest_catalog, ingest_entries  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reembed", action="store_true", help="Recompute embeddings for every entry")
    args = ap.parse_args()
    init_db()
    with SessionLocal() as db:
        print("catalog:", ingest_catalog(db))
        print("entries:", ingest_entries(db, reembed=args.reembed))
    print("embedder:", get_embedder().name)


if __name__ == "__main__":
    main()
