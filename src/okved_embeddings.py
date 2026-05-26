"""OKVED semantic search via sentence-transformers embeddings.

Usage:
  1. Pre-compute once:  python scripts/build_okved_index.py
  2. At runtime:        load_index() → search_similar(query, ...)

The index is a numpy matrix (N × dim) stored in data/okved_embeddings.npy
alongside a JSON file mapping row index → OKVED code.
"""
import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_INDEX_NPY = "data/okved_embeddings.npy"
DEFAULT_INDEX_META = "data/okved_embeddings_meta.json"

# Module-level encoder cache — loaded at most once per process.
_encoder_cache: dict = {}


def _get_encoder(model_name: str = DEFAULT_MODEL):
    if model_name not in _encoder_cache:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for semantic OKVED search. "
                "Run: pip install sentence-transformers"
            ) from exc
        logger.info("[okved_embeddings] Loading encoder '%s'...", model_name)
        _encoder_cache[model_name] = SentenceTransformer(model_name)
        logger.info("[okved_embeddings] Encoder ready")
    return _encoder_cache[model_name]


def _index_entries(reference: dict) -> list[tuple[str, str]]:
    """Return (code, title) pairs for entries at group level or deeper (XX.XX+)."""
    return [
        (code, entry.title)
        for code, entry in reference.items()
        if re.fullmatch(r"\d{2}\.\d{1,2}(?:\.\d{1,2})?", code)
    ]


def build_okved_index(
    reference: dict,
    model_name: str = DEFAULT_MODEL,
) -> tuple[np.ndarray, list[str]]:
    """Compute normalised embeddings for all OKVED entries at XX.XX level and deeper.

    Returns:
        embeddings: float32 array of shape (N, dim), L2-normalised
        codes: list of N OKVED code strings (same order as rows)
    """
    entries = _index_entries(reference)
    codes = [code for code, _ in entries]
    # Prepend code so the model sees "41.20 Строительство жилых и нежилых зданий"
    texts = [f"{code} {title}" for code, title in entries]

    logger.info("[build_okved_index] Encoding %d entries...", len(texts))
    encoder = _get_encoder(model_name)
    embeddings = encoder.encode(
        texts,
        batch_size=128,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    logger.info("[build_okved_index] Done. Shape: %s", embeddings.shape)
    return embeddings.astype(np.float32), codes


def save_index(
    embeddings: np.ndarray,
    codes: list[str],
    npy_path: str = DEFAULT_INDEX_NPY,
    meta_path: str = DEFAULT_INDEX_META,
) -> None:
    np.save(npy_path, embeddings)
    Path(meta_path).write_text(json.dumps(codes, ensure_ascii=False), encoding="utf-8")
    logger.info("[save_index] Saved %d vectors → %s", len(codes), npy_path)


@lru_cache(maxsize=2)
def load_index(
    npy_path: str = DEFAULT_INDEX_NPY,
    meta_path: str = DEFAULT_INDEX_META,
) -> Optional[tuple[np.ndarray, list[str]]]:
    """Load pre-computed index from disk. Returns None if not found."""
    if not Path(npy_path).exists() or not Path(meta_path).exists():
        logger.debug("[load_index] Index not found at %s", npy_path)
        return None
    embeddings = np.load(npy_path)
    codes = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    logger.info("[load_index] Loaded %d vectors from %s", len(codes), npy_path)
    return embeddings, codes


def search_similar(
    query: str,
    embeddings: np.ndarray,
    codes: list[str],
    top_k: int = 20,
    model_name: str = DEFAULT_MODEL,
) -> list[str]:
    """Return top-k OKVED codes most semantically similar to query.

    Uses cosine similarity (embeddings are pre-normalised, so this is a dot product).
    """
    encoder = _get_encoder(model_name)
    query_vec = encoder.encode(
        [query], normalize_embeddings=True, convert_to_numpy=True
    )
    scores = (embeddings @ query_vec.T).flatten()
    top_idx = np.argsort(scores)[::-1][:top_k]
    return [codes[i] for i in top_idx]
