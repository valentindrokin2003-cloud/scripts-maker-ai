"""Tests for okved_embeddings module — run without sentence-transformers installed."""
import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.okved_embeddings import (
    DEFAULT_INDEX_META,
    DEFAULT_INDEX_NPY,
    _index_entries,
    load_index,
    save_index,
    search_similar,
)
from src.okved_resolver import OkvedEntry


def _make_entry(code: str, title: str) -> OkvedEntry:
    return OkvedEntry(code=code, title=title, normalized_title=title.lower(), tokens=frozenset())


def _make_reference() -> dict:
    return {
        "F": _make_entry("F", "Строительство"),
        "41": _make_entry("41", "Строительство зданий"),
        "41.1": _make_entry("41.1", "Разработка строительных проектов"),
        "41.10": _make_entry("41.10", "Разработка строительных проектов"),
        "41.20": _make_entry("41.20", "Строительство жилых и нежилых зданий"),
        "43.11": _make_entry("43.11", "Разборка и снос зданий"),
        "43.21": _make_entry("43.21", "Производство электромонтажных работ"),
    }


class TestIndexEntries:
    def test_excludes_section_and_class(self):
        ref = _make_reference()
        entries = _index_entries(ref)
        codes = [c for c, _ in entries]
        assert "F" not in codes
        assert "41" not in codes

    def test_includes_group_and_deeper(self):
        ref = _make_reference()
        entries = _index_entries(ref)
        codes = [c for c, _ in entries]
        assert "41.1" in codes
        assert "41.10" in codes
        assert "41.20" in codes
        assert "43.11" in codes

    def test_entry_title_is_raw_okved_title(self):
        ref = _make_reference()
        entries = _index_entries(ref)
        entry_map = dict(entries)
        assert entry_map["41.20"] == "Строительство жилых и нежилых зданий"


class TestSaveLoadIndex:
    def test_roundtrip(self, tmp_path):
        npy = str(tmp_path / "emb.npy")
        meta = str(tmp_path / "meta.json")

        emb = np.random.rand(5, 8).astype(np.float32)
        codes = ["41.10", "41.20", "43.11", "43.21", "47.26"]

        save_index(emb, codes, npy_path=npy, meta_path=meta)

        result = load_index.__wrapped__(npy, meta)  # bypass lru_cache
        assert result is not None
        loaded_emb, loaded_codes = result
        np.testing.assert_array_almost_equal(loaded_emb, emb)
        assert loaded_codes == codes

    def test_load_returns_none_when_missing(self, tmp_path):
        result = load_index.__wrapped__(
            str(tmp_path / "missing.npy"),
            str(tmp_path / "missing.json"),
        )
        assert result is None


class TestSearchSimilar:
    def test_returns_top_k(self):
        dim = 8
        n = 10
        emb = np.random.rand(n, dim).astype(np.float32)
        # Normalise rows
        emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
        codes = [f"code_{i}" for i in range(n)]

        mock_encoder = MagicMock()
        query_vec = np.random.rand(1, dim).astype(np.float32)
        query_vec /= np.linalg.norm(query_vec)
        mock_encoder.encode.return_value = query_vec

        with patch("src.okved_embeddings._get_encoder", return_value=mock_encoder):
            result = search_similar("строительство", emb, codes, top_k=3)

        assert len(result) == 3
        assert all(c in codes for c in result)

    def test_most_similar_is_first(self):
        dim = 4
        # Two entries: one very similar to query, one orthogonal
        query_vec = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        emb = np.array([
            [1.0, 0.0, 0.0, 0.0],  # same direction — most similar
            [0.0, 1.0, 0.0, 0.0],  # orthogonal
        ], dtype=np.float32)
        codes = ["best_match", "unrelated"]

        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = query_vec

        with patch("src.okved_embeddings._get_encoder", return_value=mock_encoder):
            result = search_similar("anything", emb, codes, top_k=2)

        assert result[0] == "best_match"
        assert result[1] == "unrelated"
