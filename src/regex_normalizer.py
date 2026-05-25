import re
from collections import defaultdict

_SEP = r"[-/ ]*"
_BOUNDARY = r"\b"
_FREE_END_RE = re.compile(r"\\w(?:\{0?,?\d+\}|\*)")


def _is_free_pattern(pattern: str) -> bool:
    return bool(_FREE_END_RE.search(pattern))


def _extract_literal_stems(pattern: str) -> tuple[str, ...]:
    """Extract top-level Cyrillic/Latin stems (depth 0) for comparison."""
    stems = []
    depth = 0
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\":
            i += 2
            continue
        if c == "(":
            depth += 1
            i += 1
            continue
        if c == ")":
            depth -= 1
            i += 1
            continue
        if depth == 0 and re.match(r"[а-яёa-z]", c, re.IGNORECASE):
            j = i
            while j < len(pattern) and re.match(r"[а-яёa-z]", pattern[j], re.IGNORECASE):
                j += 1
            word = pattern[i:j].lower()
            if len(word) >= 3:
                stems.append(word)
            i = j
            continue
        i += 1
    return tuple(stems)


def _split_on_sep(pattern: str) -> tuple[str, str] | None:
    """
    Find the first [-/ ]* at parenthesis depth 0 and split there.
    Returns (left, right) or None if no separator found.
    """
    depth = 0
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\":
            i += 2
            continue
        if c == "(":
            depth += 1
            i += 1
            continue
        if c == ")":
            depth -= 1
            i += 1
            continue
        if depth == 0 and pattern[i : i + len(_SEP)] == _SEP:
            return pattern[:i], pattern[i + len(_SEP) :]
        i += 1
    return None


def _stems_prefix_match(free: tuple[str, ...], explicit: tuple[str, ...]) -> bool:
    """True if every stem in free is a prefix (≥4 chars) of the paired stem in explicit.

    Sorts both tuples so A+B and B+A patterns are treated as equivalent.
    This handles the case where build_local_regex truncates a stem
    (e.g. кремнез from кремнезем) while Stage 2 uses the full form.
    """
    if len(free) != len(explicit):
        return False
    for a, b in zip(sorted(free), sorted(explicit)):
        if a == b:
            continue
        if len(a) < 4 or len(b) < 4:
            return False
        if not b.startswith(a):
            return False
    return True


def deduplicate_free(patterns: list[str]) -> list[str]:
    """Remove \\w{0,N} patterns when an explicit-ending pattern covers the same stems.

    Handles two cases:
    - Exact stem match: (пирогенн, семинар) vs (пирогенн, семинар)
    - Prefix stem match: (пирогенн, кремнез) vs (пирогенн, кремнезем)
      where build_local_regex truncated 'кремнезем' → 'кремнез' via ENDINGS.
    """
    by_stems: dict[tuple, list[str]] = defaultdict(list)
    for p in patterns:
        by_stems[_extract_literal_stems(p)].append(p)

    explicit_stems = [
        _extract_literal_stems(p)
        for p in patterns
        if not _is_free_pattern(p)
    ]

    result = []
    seen: set[str] = set()
    for p in patterns:
        if p in seen:
            continue
        seen.add(p)
        if not _is_free_pattern(p):
            result.append(p)
            continue
        stems = _extract_literal_stems(p)
        # Exact match: there is an explicit pattern with identical stems
        if any(not _is_free_pattern(q) for q in by_stems[stems]):
            continue
        # Prefix match: there is an explicit pattern whose stems extend our stems
        if any(_stems_prefix_match(stems, es) for es in explicit_stems):
            continue
        result.append(p)
    return result


def group_by_left(patterns: list[str]) -> list[str]:
    """
    Group patterns with identical left parts into a single alternation.
    \\bA[-/ ]*B\\b + \\bA[-/ ]*C\\b  →  \\bA[-/ ]*(?:B|C)\\b
    Only patterns with clear \\b...[-/ ]*...\\b structure are grouped.
    """
    groups: dict[str, list[str]] = defaultdict(list)
    ungroupable: list[str] = []

    for p in patterns:
        split = _split_on_sep(p)
        if (
            split is None
            or not split[0].startswith(_BOUNDARY)
            or not split[1].endswith(_BOUNDARY)
        ):
            ungroupable.append(p)
            continue
        left, right = split
        groups[left].append(right)

    result = list(ungroupable)
    for left, rights in groups.items():
        flat: list[str] = []
        for r in rights:
            flat.extend(_flatten_right(r))
        rights = _deduplicate_list(flat)
        if len(rights) == 1:
            result.append(left + _SEP + rights[0])
        else:
            inner = [r[: -len(_BOUNDARY)] if r.endswith(_BOUNDARY) else r for r in rights]
            inner = _prune_subsumed_alts(inner)
            if len(inner) == 1:
                result.append(left + _SEP + inner[0] + _BOUNDARY)
            else:
                merged = "(?:" + "|".join(inner) + ")" + _BOUNDARY
                result.append(left + _SEP + merged)
    return result


def _deduplicate_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _split_top_level_alts(s: str) -> list[str]:
    """Split on | at parenthesis depth 0, respecting \\-escapes."""
    parts: list[str] = []
    depth = start = i = 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
        elif s[i] == "|" and depth == 0:
            parts.append(s[start:i])
            start = i + 1
        i += 1
    parts.append(s[start:])
    return parts


_SIMPLE_ALT_RE = re.compile(r"^(.+?)\\w\{0,(\d+)\}$")


def _prune_subsumed_alts(inners: list[str]) -> list[str]:
    """Remove alternatives whose stem is already covered by a shorter free-ending alternative.

    E.g. ['кремнез\\w{0,3}', 'кремнезем\\w{0,3}'] → ['кремнез\\w{0,3}']
    because 'кремнезем' starts with 'кремнез' and the extra 2 chars fit within \\w{0,3}.
    """
    parsed: list[tuple[str, int] | None] = []
    for inner in inners:
        m = _SIMPLE_ALT_RE.match(inner)
        parsed.append((m.group(1), int(m.group(2))) if m else None)

    to_remove: set[int] = set()
    for i, pi in enumerate(parsed):
        if pi is None or i in to_remove:
            continue
        stem_i, n_i = pi
        for j, pj in enumerate(parsed):
            if i == j or j in to_remove or pj is None:
                continue
            stem_j, _ = pj
            extra = len(stem_j) - len(stem_i)
            if stem_j.startswith(stem_i) and 0 < extra <= n_i:
                to_remove.add(j)

    return [a for k, a in enumerate(inners) if k not in to_remove]


def _flatten_right(right: str) -> list[str]:
    """Unpack ``(?:X|Y)\\b`` → ``['X\\b', 'Y\\b']``. Otherwise ``[right]``."""
    if right.startswith("(?:") and right.endswith(_BOUNDARY):
        inner = right[3 : -len(_BOUNDARY) - 1]  # strip (?:  and  )\b
        alts = _split_top_level_alts(inner)
        if len(alts) > 1:
            return [a + _BOUNDARY for a in alts]
    return [right]


def _flatten_left(left: str) -> list[str]:
    """Unpack ``\\b(?:X|Y)`` → ``['\\bX', '\\bY']``. Otherwise ``[left]``."""
    prefix = _BOUNDARY + "(?:"
    if left.startswith(prefix) and left.endswith(")"):
        inner = left[len(prefix) : -1]
        alts = _split_top_level_alts(inner)
        if len(alts) > 1:
            return [_BOUNDARY + a for a in alts]
    return [left]


def group_by_right(patterns: list[str]) -> list[str]:
    """
    Group patterns with identical right parts into a single alternation.
    \\bA[-/ ]*C\\b + \\bB[-/ ]*C\\b  →  \\b(?:A|B)[-/ ]*C\\b
    Handles reverse pairs that share the same right modifier.
    """
    groups: dict[str, list[str]] = defaultdict(list)
    ungroupable: list[str] = []

    for p in patterns:
        split = _split_on_sep(p)
        if (
            split is None
            or not split[0].startswith(_BOUNDARY)
            or not split[1].endswith(_BOUNDARY)
        ):
            ungroupable.append(p)
            continue
        left, right = split
        groups[right].append(left)

    result = list(ungroupable)
    for right, lefts in groups.items():
        flat: list[str] = []
        for l in lefts:
            flat.extend(_flatten_left(l))
        lefts = _deduplicate_list(flat)
        if len(lefts) == 1:
            result.append(lefts[0] + _SEP + right)
        else:
            inner = [l[len(_BOUNDARY):] if l.startswith(_BOUNDARY) else l for l in lefts]
            merged = _BOUNDARY + "(?:" + "|".join(inner) + ")"
            result.append(merged + _SEP + right)
    return result


def normalize(patterns: list[str]) -> list[str]:
    """
    Post-process regex patterns:
    1. Remove \\w{0,N} patterns when explicit-ending version covers same stems (pre-group pass).
    2. Group by common left stem  (A+B, A+C → A+(?:B|C))
    3. Group by common right stem (A+C, B+C → (?:A|B)+C)
    4. Remove remaining \\w{0,N} patterns whose merged stems match an explicit (post-group pass).
    """
    patterns = deduplicate_free(patterns)
    patterns = group_by_left(patterns)
    patterns = group_by_right(patterns)
    patterns = deduplicate_free(patterns)
    return patterns
