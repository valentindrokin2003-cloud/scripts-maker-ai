import re
import pytest
from src.regex_builder_stage2 import (
    _adj_stem,
    _noun_stem_and_key,
    _resolve,
    build_regex_from_spec,
)


# ── Stem extraction ───────────────────────────────────────────────────────────

class TestAdjStem:
    def test_iy_ending(self):
        assert _adj_stem("бухгалтерский") == "бухгалтерск"

    def test_yy_ending(self):
        assert _adj_stem("оцинкованный") == "оцинкованн"

    def test_oy_ending(self):
        assert _adj_stem("выездной") == "выездн"

    def test_aya_ending(self):
        # LLM may produce feminine form; still handled
        assert _adj_stem("металлическая") == "металлическ"

    def test_oe_ending(self):
        assert _adj_stem("консалтинговое") == "консалтингов"

    def test_short_word_not_stripped(self):
        # Word too short — returned as-is rather than giving nonsensical stem
        result = _adj_stem("ой")
        assert result == "ой"

    def test_konsaltingovyy(self):
        assert _adj_stem("консалтинговый") == "консалтингов"


class TestNounStemAndKey:
    def test_feminine_a(self):
        stem, key = _noun_stem_and_key("услуга")
        assert stem == "услуг"
        assert key == "noun_f"

    def test_feminine_a_lenta(self):
        stem, key = _noun_stem_and_key("лента")
        assert stem == "лент"
        assert key == "noun_f"

    def test_feminine_ia(self):
        stem, key = _noun_stem_and_key("конференция")
        assert stem == "конференц"
        assert key == "noun_fia"

    def test_feminine_ia_akciya(self):
        stem, key = _noun_stem_and_key("акция")
        assert stem == "акц"
        assert key == "noun_fia"

    def test_masculine_zero(self):
        stem, key = _noun_stem_and_key("консалтинг")
        assert stem == "консалтинг"
        assert key == "noun_m"

    def test_masculine_seminar(self):
        stem, key = _noun_stem_and_key("семинар")
        assert stem == "семинар"
        assert key == "noun_m"

    def test_masculine_outsourcing(self):
        stem, key = _noun_stem_and_key("аутсорсинг")
        assert stem == "аутсорсинг"
        assert key == "noun_m"

    def test_neuter_nie(self):
        stem, key = _noun_stem_and_key("покрытие")
        assert stem == "покрыт"
        assert key == "noun_nie"

    def test_neuter_no(self):
        stem, key = _noun_stem_and_key("масло")
        assert stem == "масл"
        assert key == "noun_no"

    def test_soft_sign(self):
        stem, key = _noun_stem_and_key("соль")
        assert stem == "сол"
        assert key == "noun_sf"


# ── Pattern correctness ───────────────────────────────────────────────────────

def _matches(pattern: str, text: str) -> bool:
    return bool(re.search(pattern, text))


class TestWordPatterns:
    def test_adj_nominative_matches(self):
        stem, ends = _resolve("бухгалтерский", "adj")
        p = rf"\b{re.escape(stem)}{ends}\b"
        assert _matches(p, "бухгалтерский учёт")
        assert _matches(p, "бухгалтерского аутсорсинга")
        assert _matches(p, "бухгалтерские услуги")

    def test_noun_f_all_cases(self):
        stem, ends = _resolve("услуга", "noun")
        p = rf"\b{re.escape(stem)}{ends}\b"
        assert _matches(p, "оплата услуга")
        assert _matches(p, "оплата услуги")
        assert _matches(p, "оплата услугу")
        assert _matches(p, "оплата услугой")
        assert _matches(p, "оплата услугам")

    def test_noun_fia_all_cases(self):
        stem, ends = _resolve("конференция", "noun")
        p = rf"\b{re.escape(stem)}{ends}\b"
        assert _matches(p, "выездная конференция")
        assert _matches(p, "оплата конференции")
        assert _matches(p, "на конференцию")
        assert _matches(p, "о конференциях")

    def test_noun_m_all_cases(self):
        stem, ends = _resolve("семинар", "noun")
        p = rf"\b{re.escape(stem)}{ends}\b"
        assert _matches(p, "семинар")
        assert _matches(p, "семинара")
        assert _matches(p, "семинары")
        assert _matches(p, "семинарам")

    def test_free_ending_default(self):
        # noun_m: max ending is 3 chars (ами) → \w{0,3}
        stem, ends = _resolve("семинар", "noun")
        assert ends == r"\w{0,3}"

    def test_free_ending_fia(self):
        # noun_fia: max ending is 4 chars (иями) → \w{0,4}
        stem, ends = _resolve("конференция", "noun")
        assert ends == r"\w{0,4}"

    def test_free_ending_no(self):
        # noun_no: max ending is 2 chars (ом) → \w{0,2}
        stem, ends = _resolve("масло", "noun")
        assert ends == r"\w{0,2}"

    def test_free_ending_adj(self):
        # adj: max ending is 3 chars (ого) → \w{0,3}
        stem, ends = _resolve("бухгалтерский", "adj")
        assert ends == r"\w{0,3}"

    def test_ambiguous_uses_explicit_endings(self):
        # ambiguous=True → explicit endings to prevent false positives (сыр → сырьё)
        stem, ends = _resolve("сыр", "noun", ambiguous=True)
        assert stem == "сыр"
        assert r"\w" not in ends
        assert "а" in ends  # explicit genitive endings

    def test_ambiguous_false_positive_prevented(self):
        # With explicit endings, сыр should NOT match сырьё
        stem, ends = _resolve("сыр", "noun", ambiguous=True)
        p = rf"\b{re.escape(stem)}{ends}\b"
        assert _matches(p, "сыр")
        assert _matches(p, "сыра")
        assert not _matches(p, "сырьё")
        assert not _matches(p, "сырой")

    def test_free_ending_matches_all_forms(self):
        # Free ending is permissive enough to cover common inflections
        stem, ends = _resolve("конференция", "noun")
        p = rf"\b{re.escape(stem)}{ends}\b"
        assert _matches(p, "конференция")
        assert _matches(p, "конференции")
        assert _matches(p, "конференцию")
        assert _matches(p, "конференциях")
        assert _matches(p, "конференциями")

    def test_brand_exact(self):
        stem, ends = _resolve("ecolab", "brand")
        p = rf"\b{re.escape(stem)}{ends}\b"
        assert _matches(p, "ecolab")
        assert not _matches(p, "ecolabing")

    def test_pattern_is_valid_regex(self):
        for word, pos in [
            ("металлический", "adj"), ("консалтинговый", "adj"),
            ("услуга", "noun"), ("конференция", "noun"), ("масло", "noun"),
            ("ecolab", "brand"),
        ]:
            stem, ends = _resolve(word, pos)
            re.compile(rf"\b{re.escape(stem)}{ends}\b")


# ── build_regex_from_spec ─────────────────────────────────────────────────────

class TestBuildRegexFromSpec:

    def test_standalone_noun_only(self):
        spec = {"concepts": [
            {"base_word": "аутсорсинг", "pos": "noun", "standalone": True, "pairs": []}
        ]}
        patterns = build_regex_from_spec(spec)
        assert len(patterns) == 1
        assert _matches(patterns[0], "бухгалтерский аутсорсинг")
        assert _matches(patterns[0], "аутсорсинга")

    def test_standalone_false_with_no_pairs_emits_nothing(self):
        spec = {"concepts": [
            {"base_word": "услуга", "pos": "noun", "standalone": False, "pairs": []}
        ]}
        patterns = build_regex_from_spec(spec)
        assert patterns == []

    def test_single_pair_forward_and_reverse(self):
        spec = {"concepts": [
            {"base_word": "бухгалтерский", "pos": "adj", "standalone": False,
             "pairs": [{"with": "услуга"}]},
            {"base_word": "услуга", "pos": "noun", "standalone": False, "pairs": []},
        ]}
        patterns = build_regex_from_spec(spec)
        assert len(patterns) == 2
        fwd, rev = patterns[0], patterns[1]
        assert _matches(fwd, "бухгалтерские услуги")
        assert _matches(rev, "услуги бухгалтерской")
        for p in patterns:
            re.compile(p)

    def test_multiple_pairs_grouped(self):
        spec = {"concepts": [
            {"base_word": "бухгалтерский", "pos": "adj", "standalone": False,
             "pairs": [{"with": "услуга"}, {"with": "аутсорсинг"}]},
            {"base_word": "услуга", "pos": "noun", "standalone": False, "pairs": []},
            {"base_word": "аутсорсинг", "pos": "noun", "standalone": True, "pairs": []},
        ]}
        patterns = build_regex_from_spec(spec)

        # standalone аутсорсинг + fwd grouped + rev grouped = 3
        assert len(patterns) == 3
        fwd = next(p for p in patterns if p.startswith(r"\bбухгалтерск"))
        rev = next(p for p in patterns if "услуг" in p and p.startswith(r"\b(?:"))

        assert _matches(fwd, "бухгалтерские услуги")
        assert _matches(fwd, "бухгалтерского аутсорсинга")
        assert _matches(rev, "услуга бухгалтерской")
        assert _matches(rev, "аутсорсинг бухгалтерский")
        for p in patterns:
            re.compile(p)

    def test_grouped_выездной_three_pairs(self):
        spec = {"concepts": [
            {"base_word": "выездной", "pos": "adj", "standalone": False,
             "pairs": [
                 {"with": "семинар"},
                 {"with": "корпоратив"},
                 {"with": "конференция"},
             ]},
            {"base_word": "семинар", "pos": "noun", "standalone": False, "pairs": []},
            {"base_word": "корпоратив", "pos": "noun", "standalone": False, "pairs": []},
            {"base_word": "конференция", "pos": "noun", "standalone": False, "pairs": []},
        ]}
        patterns = build_regex_from_spec(spec)

        # Only forward + reverse (2 grouped patterns, no standalone)
        assert len(patterns) == 2
        fwd = patterns[0]
        rev = patterns[1]

        assert _matches(fwd, "выездной семинар")
        assert _matches(fwd, "выездного корпоратива")
        assert _matches(fwd, "выездные конференции")
        assert _matches(rev, "семинара выездного")
        assert _matches(rev, "конференций выездных")
        for p in patterns:
            re.compile(p)

    def test_no_duplicate_patterns(self):
        spec = {"concepts": [
            {"base_word": "консалтинговый", "pos": "adj", "standalone": False,
             "pairs": [{"with": "услуга"}]},
            # услуга appears again as a separate concept — should not duplicate patterns
            {"base_word": "услуга", "pos": "noun", "standalone": False, "pairs": []},
            {"base_word": "бухгалтерский", "pos": "adj", "standalone": False,
             "pairs": [{"with": "услуга"}]},
        ]}
        patterns = build_regex_from_spec(spec)
        assert len(patterns) == len(set(patterns))

    def test_brand_exact_match(self):
        spec = {"concepts": [
            {"base_word": "ecolab", "pos": "brand", "standalone": True, "pairs": []},
        ]}
        patterns = build_regex_from_spec(spec)
        assert len(patterns) == 1
        assert _matches(patterns[0], "средство ecolab")
        assert not _matches(patterns[0], "ecolabbed")
        re.compile(patterns[0])

    def test_ambiguous_concept_uses_explicit_endings(self):
        spec = {"concepts": [
            {"base_word": "сыр", "pos": "noun", "standalone": True, "ambiguous": True, "pairs": []},
        ]}
        patterns = build_regex_from_spec(spec)
        assert len(patterns) == 1
        p = patterns[0]
        assert _matches(p, "сыр")
        assert _matches(p, "сыра")
        assert not _matches(p, "сырьё")
        assert not _matches(p, "сырой")
        re.compile(p)

    def test_non_ambiguous_concept_uses_free_ending(self):
        spec = {"concepts": [
            {"base_word": "семинар", "pos": "noun", "standalone": True, "ambiguous": False, "pairs": []},
        ]}
        patterns = build_regex_from_spec(spec)
        assert r"\w{0,3}" in patterns[0]

    def test_fia_noun_uses_wider_free_ending(self):
        spec = {"concepts": [
            {"base_word": "конференция", "pos": "noun", "standalone": True, "ambiguous": False, "pairs": []},
        ]}
        patterns = build_regex_from_spec(spec)
        assert r"\w{0,4}" in patterns[0]

    def test_ambiguous_base_word_takes_precedence_over_pair_target(self):
        # If сыр appears as base_word with ambiguous=True and also as a pair target,
        # explicit endings must be used (base_word registration wins).
        spec = {"concepts": [
            {"base_word": "сыр", "pos": "noun", "standalone": True, "ambiguous": True, "pairs": []},
            {"base_word": "твёрдый", "pos": "adj", "standalone": False, "ambiguous": False,
             "pairs": [{"with": "сыр"}]},
        ]}
        patterns = build_regex_from_spec(spec)
        standalone = next(p for p in patterns if p.startswith(r"\bсыр"))
        assert not _matches(standalone, "сырьё")

    def test_empty_concepts(self):
        assert build_regex_from_spec({}) == []
        assert build_regex_from_spec({"concepts": []}) == []

    def test_stem_correctness_no_double_suffix(self):
        """Pattern must not contain the full nominative form as 'stem' prefix."""
        spec = {"concepts": [
            {"base_word": "бухгалтерский", "pos": "adj", "standalone": True, "pairs": []},
        ]}
        patterns = build_regex_from_spec(spec)
        # Stem should be 'бухгалтерск', not 'бухгалтерский'
        assert "бухгалтерскийого" not in patterns[0]
        assert "бухгалтерск" in patterns[0]

    def test_word_separator_no_optconn(self):
        """Pairs should use simple [-/ ]* separator, not the optional-preposition form."""
        spec = {"concepts": [
            {"base_word": "выездной", "pos": "adj", "standalone": False,
             "pairs": [{"with": "семинар"}]},
            {"base_word": "семинар", "pos": "noun", "standalone": False, "pairs": []},
        ]}
        patterns = build_regex_from_spec(spec)
        for p in patterns:
            assert r"[-/ ]*" in p
