"""Replaceable embedding providers.

No commercial vendor is hardcoded as a required dependency. The default
HashEmbeddingProvider is deterministic and local so tests and offline demos
work without sending document text to an external model.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol, Sequence

from django.conf import settings

VECTOR_SIZE = 64


class EmbeddingProvider(Protocol):
    name: str

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


class HashEmbeddingProvider:
    """Local, non-semantic embeddings derived from token hashes.

    Useful as a pluggable default. Cosine scores from this provider are not
    calibrated semantic relevance.
    """

    name = "hash"

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * VECTOR_SIZE
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = digest[0] % VECTOR_SIZE
            vector[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class NullEmbeddingProvider:
    name = "none"

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [[] for _ in texts]


def get_embedding_provider() -> EmbeddingProvider:
    name = getattr(settings, "EMBEDDING_PROVIDER", "hash")
    if name in ("hash", "local"):
        return HashEmbeddingProvider()
    if name in ("none", "off"):
        return NullEmbeddingProvider()
    raise RuntimeError(
        f"Unknown EMBEDDING_PROVIDER '{name}'. Configure a supported provider "
        "or implement knowledge.embeddings.EmbeddingProvider."
    )


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))
