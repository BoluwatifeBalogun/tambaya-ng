"""Embedding component (report §2.5.2 items 4 and 6).

Groq does not offer an embeddings endpoint, so embeddings are computed locally:
- default: a deterministic hashed n-gram embedder (no downloads, works offline, used for every audit);
- optional: a sentence-transformers model set in LOCAL_EMBED_MODEL (e.g. intfloat/multilingual-e5-small).
The active embedder name is persisted on every entry and surfaced by /api/health."""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from functools import lru_cache

from ..config import get_settings

LOCAL_NAME = "local-hashed-ngram-v1"


def _norm(vec: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ɓɗƙƴ' ]+", " ", text)


def local_embed(text: str, dim: int) -> list[float]:
    """Hashed word unigrams + bigrams + character 3..5-grams, log-scaled, signed hashing (feature hashing)."""
    vec = [0.0] * dim
    folded = _fold(text)
    words = folded.split()
    feats: list[str] = []
    feats += [f"w:{w}" for w in words]
    feats += [f"b:{a}_{b}" for a, b in zip(words, words[1:])]
    padded = f" {' '.join(words)} "
    for n in (3, 4, 5):
        feats += [f"c{n}:{padded[i:i+n]}" for i in range(len(padded) - n + 1)]
    counts: dict[str, int] = {}
    for f in feats:
        counts[f] = counts.get(f, 0) + 1
    for f, c in counts.items():
        h = hashlib.blake2b(f.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(h[:4], "little") % dim
        sign = 1.0 if h[4] & 1 else -1.0
        weight = 1.0 + math.log(c)
        if f.startswith("w:"):
            weight *= 2.0  # whole words matter more than character fragments
        vec[idx] += sign * weight
    return _norm(vec)


class Embedder:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.dim = self.settings.embed_dim
        self._st = None
        if self.settings.local_embed_model:
            try:  # pragma: no cover - optional dependency
                from sentence_transformers import SentenceTransformer

                self._st = SentenceTransformer(self.settings.local_embed_model)
            except Exception:  # pragma: no cover
                self._st = None

    @property
    def name(self) -> str:
        return f"st:{self.settings.local_embed_model}" if self._st is not None else LOCAL_NAME

    @property
    def is_model(self) -> bool:
        """True when a neural embedding model (not the hashed embedder) is active."""
        return self._st is not None

    def embed(self, texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        if not texts:
            return []
        if self._st is not None:  # pragma: no cover
            prefix = "query: " if task == "RETRIEVAL_QUERY" else "passage: "  # e5 convention; harmless for others
            vecs = self._st.encode([prefix + t for t in texts], normalize_embeddings=True)
            return [_norm([float(x) for x in v][: self.dim]) for v in vecs]
        return [local_embed(t, self.dim) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text], task="RETRIEVAL_QUERY")[0]


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()
