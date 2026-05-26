#!/usr/bin/env python3
"""Pre-compute sentence-transformer embeddings for the OKVED reference.

Run once from the project root:
    venv/bin/python scripts/build_okved_index.py

Produces:
    data/okved_embeddings.npy   — float32 matrix (N × 384)
    data/okved_embeddings_meta.json — list of N OKVED codes

The files are loaded at inference time by src/okved_embeddings.load_index().
Re-run if data/Kod_Okved-2.xlsx is ever updated.
"""
import logging
import sys
from pathlib import Path

# Allow running from repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from src.okved_embeddings import DEFAULT_INDEX_META, DEFAULT_INDEX_NPY, DEFAULT_MODEL, build_okved_index, save_index
from src.okved_resolver import DEFAULT_OKVED_PATH, load_okved_reference


def main() -> None:
    logger.info("Loading OKVED reference from %s", DEFAULT_OKVED_PATH)
    reference = load_okved_reference(DEFAULT_OKVED_PATH)
    logger.info("Reference loaded: %d entries", len(reference))

    embeddings, codes = build_okved_index(reference, model_name=DEFAULT_MODEL)

    save_index(embeddings, codes, npy_path=DEFAULT_INDEX_NPY, meta_path=DEFAULT_INDEX_META)
    logger.info("Index ready: %d codes, embedding dim %d", len(codes), embeddings.shape[1])
    logger.info("Files written:")
    logger.info("  %s", DEFAULT_INDEX_NPY)
    logger.info("  %s", DEFAULT_INDEX_META)


if __name__ == "__main__":
    main()
