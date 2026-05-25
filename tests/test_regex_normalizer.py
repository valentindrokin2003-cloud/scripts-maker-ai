import re
import pytest
from src.regex_normalizer import deduplicate_free, group_by_left, normalize


# ── deduplicate_free ──────────────────────────────────────────────────────────

def test_dedup_removes_free_when_explicit_exists():
    patterns = [
        r"\bвыездн\w{0,3}[-/ ]*семинар\w{0,3}\b",
        r"\bвыездн(?:ого|ому|ая|ой|ую|ые|ых)?[-/ ]*семинар(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b",
    ]
    result = deduplicate_free(patterns)
    assert len(result) == 1
    assert r"\w{0,3}" not in result[0]


def test_dedup_keeps_free_when_no_explicit():
    patterns = [r"\bвыездн\w{0,3}[-/ ]*семинар\w{0,3}\b"]
    assert deduplicate_free(patterns) == patterns


def test_dedup_keeps_both_when_different_stems():
    patterns = [
        r"\bвыездн\w{0,3}[-/ ]*семинар\w{0,3}\b",
        r"\bвыездн\w{0,3}[-/ ]*корпоратив\w{0,3}\b",
    ]
    result = deduplicate_free(patterns)
    assert len(result) == 2


def test_dedup_removes_multiple_free_versions():
    patterns = [
        r"\bвыездн\w{0,3}[-/ ]*семинар\w{0,3}\b",
        r"\bвыездн\w*[-/ ]*семинар\w*\b",
        r"\bвыездн(?:ого|ому|ая|ой)?[-/ ]*семинар(?:а|у|ом)?\b",
    ]
    result = deduplicate_free(patterns)
    assert len(result) == 1
    assert r"\w" not in result[0]


def test_dedup_preserves_order_of_remaining():
    patterns = [
        r"\bвейп(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b",
        r"\bвыездн\w{0,3}[-/ ]*семинар\w{0,3}\b",
        r"\bвыездн(?:ого|ому|ая|ой)?[-/ ]*семинар(?:а|у|ом)?\b",
    ]
    result = deduplicate_free(patterns)
    assert result[0].startswith(r"\bвейп")


# ── group_by_left ─────────────────────────────────────────────────────────────

def test_group_merges_two_patterns_with_same_left():
    patterns = [
        r"\bвыездн(?:ого|ому|ая|ой)?[-/ ]*семинар(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b",
        r"\bвыездн(?:ого|ому|ая|ой)?[-/ ]*корпоратив(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b",
    ]
    result = group_by_left(patterns)
    assert len(result) == 1
    assert "семинар" in result[0]
    assert "корпоратив" in result[0]
    assert result[0].startswith(r"\b")
    assert result[0].endswith(r"\b")
    re.compile(result[0])


def test_group_merges_three_patterns_with_same_left():
    patterns = [
        r"\bвыездн(?:ого|ому|ая|ой)?[-/ ]*семинар(?:а|у|ом)?\b",
        r"\bвыездн(?:ого|ому|ая|ой)?[-/ ]*корпоратив(?:а|у|ом)?\b",
        r"\bвыездн(?:ого|ому|ая|ой)?[-/ ]*конференци(?:я|и|ию|ей)?\b",
    ]
    result = group_by_left(patterns)
    assert len(result) == 1
    assert "семинар" in result[0]
    assert "корпоратив" in result[0]
    assert "конференци" in result[0]
    re.compile(result[0])


def test_group_keeps_single_pattern_unchanged():
    patterns = [r"\bвыездн(?:ого|ому|ая|ой)?[-/ ]*семинар(?:а|у|ом)?\b"]
    result = group_by_left(patterns)
    assert result == patterns


def test_group_does_not_merge_different_left():
    patterns = [
        r"\bвыездн(?:ого|ому|ая|ой)?[-/ ]*семинар(?:а|у|ом)?\b",
        r"\bкорпоратив(?:а|у|ом)?[-/ ]*выездн(?:ого|ому|ая|ой)?\b",
    ]
    result = group_by_left(patterns)
    assert len(result) == 2


def test_group_leaves_single_word_pattern_alone():
    patterns = [r"\bвейп(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b"]
    result = group_by_left(patterns)
    assert result == patterns


def test_group_produces_valid_regex():
    patterns = [
        r"\bметаллическ(?:ого|ому|ая|ой|ую|ие|их)?[-/ ]*лент(?:а|ы|е|у|ой|ою|ам|ами|ах)?\b",
        r"\bметаллическ(?:ого|ому|ая|ой|ую|ие|их)?[-/ ]*труб(?:а|ы|у|е|ой|ою|ам|ами|ах)?\b",
    ]
    result = group_by_left(patterns)
    assert len(result) == 1
    re.compile(result[0])
    assert re.search(result[0], "металлическая лента")
    assert re.search(result[0], "металлической трубы")


# ── normalize (full pipeline) ─────────────────────────────────────────────────

def test_normalize_deduplicates_and_groups():
    patterns = [
        r"\bвыездн\w{0,3}[-/ ]*семинар\w{0,3}\b",
        r"\bвыездн\w{0,3}[-/ ]*корпоратив\w{0,3}\b",
        r"\bвыездн(?:ого|ому|ая|ой)?[-/ ]*семинар(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b",
        r"\bвыездн(?:ого|ому|ая|ой)?[-/ ]*корпоратив(?:а|у|ом|е|ы|ов|ам|ами|ах)?\b",
    ]
    result = normalize(patterns)
    assert len(result) == 1
    assert r"\w{0,3}" not in result[0]
    assert "семинар" in result[0]
    assert "корпоратив" in result[0]
    re.compile(result[0])


def test_normalize_real_world_выездной_case():
    patterns = [
        r"\bвыездн\w{0,3}[-/ ]*семинар\w{0,3}\b",
        r"\bвыездн\w{0,3}[-/ ]*корпоратив\w{0,3}\b",
        r"\bвыездн\w{0,3}[-/ ]*конференци\w{0,3}\b",
        r"\bсеминар\w{0,3}[-/ ]*выездн\w{0,3}\b",
        r"\bкорпоратив\w{0,3}[-/ ]*выездн\w{0,3}\b",
        r"\bконференци\w{0,3}[-/ ]*выездн\w{0,3}\b",
        r"\bвыездн(?:ого|ому|ая|ой|ую|ые|ых|ом|им)?[-/ ]*(?:семинар(?:а|у|ом|е|ы|ов|ам|ами|ах)?|корпоратив(?:а|у|ом|е|ы|ов|ам|ами|ах)?|конференци(?:я|и|ию|ей|ям|ями|ях)?)\b",
        r"\b(?:семинар(?:а|у|ом|е|ы|ов|ам|ами|ах)?|корпоратив(?:а|у|ом|е|ы|ов|ам|ами|ах)?|конференци(?:я|и|ию|ей|ям|ями|ях)?)[-/ ]*выездн(?:ого|ому|ая|ой|ую|ые|ых|ом|им)?\b",
    ]
    result = normalize(patterns)
    # Free patterns removed, already-grouped patterns kept
    for p in result:
        assert r"\w{0,3}" not in p
        re.compile(p)
    # Forward and reverse remain
    assert any("выездн" in p and p.startswith(r"\bвыездн") for p in result)
    assert any("выездн" in p and not p.startswith(r"\bвыездн") for p in result)
