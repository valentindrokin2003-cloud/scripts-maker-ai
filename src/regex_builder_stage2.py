"""Stage 2: deterministic regex builder from semantic spec.

Converts {"concepts": [...]} produced by Stage 1 (LLM) into optimized
Python regex patterns without any LLM calls.
"""
import re
from typing import Dict, List, Tuple

_SEP = r"[-/ ]*"

# Free endings keyed by noun/adj type — N is the max inflection length after the stem.
#   noun_fia: конференц + иями = 4 chars
#   noun_no:  масл     + ом   = 2 chars
#   everything else            = 3 chars (ами, ою, ими, ями …)
_FREE_ENDINGS: Dict[str, str] = {
    "noun_m":   r"\w{0,3}",
    "noun_f":   r"\w{0,3}",
    "noun_fia": r"\w{0,4}",
    "noun_nie": r"\w{0,3}",
    "noun_no":  r"\w{0,2}",
    "noun_sf":  r"\w{0,3}",
    "adj":      r"\w{0,3}",
    "brand":    r"",
}

# Explicit endings used only when concept has ambiguous=True (short/homonymous stem).
_ENDINGS: Dict[str, str] = {
    # Masculine nouns (zero nominative ending): консалтинг, семинар, аутсорсинг
    "noun_m":   r"(?:а|у|ом|е|ы|и|ов|ам|ами|ах)?",
    # Feminine nouns (-а/-я): услуга→услуг, лента→лент
    "noun_f":   r"(?:а|ы|и|е|у|ой|ою|ам|ами|ах)?",
    # Feminine nouns in -ия: конференция→конференц, акция→акц
    "noun_fia": r"(?:ия|ии|ию|ией|иям|иями|иях|ий)?",
    # Neuter nouns in -ие: покрытие→покрыт, оборудование→оборудован
    "noun_nie": r"(?:ие|ия|ию|ием|ии)?",
    # Neuter nouns in -о: масло→масл, средство→средств
    "noun_no":  r"(?:о|а|у|ом|е)?",
    # Soft-sign feminine: соль→сол, смесь→смес
    "noun_sf":  r"(?:ь|и|ей|ю|ью|ям|ями|ях)?",
    # Adjectives (hard + soft): бухгалтерск, выездн, оцинкованн
    "adj":      r"(?:ого|ому|ым|ом|ий|ый|ой|ая|ую|ое|ые|ие|ых|их|ими)?",
    # Brands / abbreviations: exact match, no endings
    "brand":    r"",
}


def _adj_stem(word: str) -> str:
    """Strip nominative adjectival suffix to obtain the inflection stem.

    бухгалтерский → бухгалтерск
    выездной      → выездн
    оцинкованный  → оцинкованн
    металлическая → металлическ
    """
    w = word.lower()
    for suf in ("ая", "ое", "ые", "ие", "ий", "ый", "ой"):
        if w.endswith(suf) and len(w) > len(suf) + 2:
            return w[: -len(suf)]
    return w


def _noun_stem_and_key(word: str) -> Tuple[str, str]:
    """Return (stem, endings_key) for a noun given its nominative singular form."""
    w = word.lower()
    # -ия / -ии: конференция, акция
    if w.endswith(("ия", "ии")) and len(w) > 3:
        return w[:-2], "noun_fia"
    # -ие: покрытие, оборудование
    if w.endswith("ие") and len(w) > 3:
        return w[:-2], "noun_nie"
    # -ье: ущелье (rare)
    if w.endswith("ье") and len(w) > 3:
        return w[:-2], "noun_nie"
    # soft-sign: соль, смесь
    if w.endswith("ь") and len(w) > 2:
        return w[:-1], "noun_sf"
    # -о: масло, средство
    if w.endswith("о") and len(w) > 3:
        return w[:-1], "noun_no"
    # -а/-я: услуга, лента, земля
    if w.endswith(("а", "я")) and len(w) > 3:
        return w[:-1], "noun_f"
    # Plural forms: strip ending to recover the singular stem.
    # -ы: семинары, тренинги (твёрдые мужской рода)
    if w.endswith("ы") and len(w) > 3:
        return w[:-1], "noun_m"
    # -и after velars/sibilants (гкхжшщч): торги→торг, ключи→ключ
    # This is the Russian spelling rule и after velars instead of ы.
    _VELARS = set("гкхжшщч")
    if w.endswith("и") and len(w) > 3 and w[-2] in _VELARS:
        return w[:-1], "noun_m"
    # -й: кремний→кремни, трамвай→трамва, гений→гени
    # Oblique forms drop й: кремния, кремнию, кремнием — stem is without й.
    if w.endswith("й") and len(w) > 3:
        return w[:-1], "noun_m"
    # default: masculine (bare consonant stem)
    return w, "noun_m"


def _resolve(base_word: str, pos: str, ambiguous: bool = False) -> Tuple[str, str]:
    """Return (stem, endings_string) ready to embed in a regex pattern.

    By default uses a free ending from _FREE_ENDINGS whose N matches the maximum
    inflection length for that word type (e.g. ``\\w{0,4}`` for -ия nouns,
    ``\\w{0,3}`` for most others).  Pass ambiguous=True for words whose stem is
    short or homonymous (e.g. сыр → сырьё) — those get explicit endings instead.
    """
    p = pos.lower()
    if p == "brand":
        return base_word.lower(), _ENDINGS["brand"]
    if p in ("adj", "adjective"):
        stem = _adj_stem(base_word)
        return stem, (_ENDINGS["adj"] if ambiguous else _FREE_ENDINGS["adj"])
    stem, key = _noun_stem_and_key(base_word)
    return stem, (_ENDINGS[key] if ambiguous else _FREE_ENDINGS[key])


def _escape_stem(stem: str) -> str:
    """Escape stem, replacing spaces with [-/ ]* so multi-word stems work correctly."""
    if " " in stem:
        return _SEP.join(re.escape(part) for part in stem.split())
    return re.escape(stem)


def _word_pattern(stem: str, ends: str) -> str:
    return rf"\b{_escape_stem(stem)}{ends}\b"


def _pair_patterns(
    base_stem: str,
    base_ends: str,
    pair_items: List[Tuple[str, str]],
) -> Tuple[str, str]:
    """Build grouped forward and reverse patterns.

    One pair  → \\bA{ea}[-/ ]*B{eb}\\b  +  reverse
    Multiple  → \\bA{ea}[-/ ]*(?:B{eb}|C{ec})\\b  +  reverse
    """
    if len(pair_items) == 1:
        ps, pe = pair_items[0]
        fwd = rf"\b{_escape_stem(base_stem)}{base_ends}{_SEP}{_escape_stem(ps)}{pe}\b"
        rev = rf"\b{_escape_stem(ps)}{pe}{_SEP}{_escape_stem(base_stem)}{base_ends}\b"
    else:
        alt = "|".join(_escape_stem(s) + e for s, e in pair_items)
        fwd = rf"\b{_escape_stem(base_stem)}{base_ends}{_SEP}(?:{alt})\b"
        rev = rf"\b(?:{alt}){_SEP}{_escape_stem(base_stem)}{base_ends}\b"
    return fwd, rev


def build_regex_from_spec(spec: Dict) -> List[str]:
    """Convert a semantic spec dict into optimized regex patterns.

    Spec format (produced by Stage 1 LLM call)::

        {
            "concepts": [
                {
                    "base_word": "бухгалтерский",   # nominative sg, masc for adj
                    "pos": "adj",                   # adj | noun | brand
                    "standalone": false,
                    "pairs": [
                        {"with": "услуга"},
                        {"with": "аутсорсинг"}
                    ]
                },
                ...
            ]
        }

    For each concept with pairs, emits one grouped forward pattern and one
    reverse, rather than N separate forward+reverse pairs — no duplicates.
    """
    raw_concepts = spec.get("concepts", [])

    # Pre-build (stem, endings) for every word mentioned.
    # Base words are registered first with their ambiguous flag;
    # pair targets are registered second (non-ambiguous by default)
    # so base-word settings always take precedence.
    index: Dict[str, Tuple[str, str]] = {}

    def _register(word: str, pos: str = "noun", ambiguous: bool = False) -> None:
        if word not in index:
            index[word] = _resolve(word, pos, ambiguous)

    for c in raw_concepts:
        _register(c["base_word"], c.get("pos", "noun"), c.get("ambiguous", False))
    for c in raw_concepts:
        for p in c.get("pairs", []):
            _register(p["with"], p.get("pos", "noun"))

    patterns: List[str] = []
    seen: set = set()

    def _add(p: str) -> None:
        if p not in seen:
            seen.add(p)
            patterns.append(p)

    for c in raw_concepts:
        bw = c["base_word"]
        if bw not in index:
            continue
        stem, ends = index[bw]
        standalone = c.get("standalone", True)
        pairs = c.get("pairs", [])

        if standalone:
            _add(_word_pattern(stem, ends))

        if not pairs:
            continue

        pair_items = [index[p["with"]] for p in pairs if p["with"] in index]
        if not pair_items:
            continue

        fwd, rev = _pair_patterns(stem, ends, pair_items)
        _add(fwd)
        _add(rev)

    return patterns
