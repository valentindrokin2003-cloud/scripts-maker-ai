import logging
from typing import Any, List

from src.regex_builder import build_local_regex, validate_regex_patterns
from src.regex_builder_stage2 import build_regex_from_spec
from src.regex_normalizer import normalize
from src.regex_spec_extractor import extract_spec
from src.settings import DEFAULT_LLM_MODEL

logger = logging.getLogger(__name__)


def _merge_patterns(*groups: List[str]) -> List[str]:
    merged = []
    seen = set()
    for group in groups:
        for pattern in validate_regex_patterns(group):
            if pattern not in seen:
                seen.add(pattern)
                merged.append(pattern)
    return merged


def generate_regex(
    product_words: List[str],
    client: Any,
    model: str = DEFAULT_LLM_MODEL,
) -> List[str]:
    """Generate regex patterns for product words using a two-stage approach.

    Stage 1 (LLM): extract a semantic spec — concepts, POS tags, pair relations.
    Stage 2 (deterministic): build explicit-ending patterns from the spec.
    Local seed patterns from regex_builder are always merged in.
    Falls back to local seeds only if Stage 1 fails.
    """
    if not product_words:
        return []

    local_patterns = build_local_regex(product_words)
    logger.info("[generate_regex] Local seed patterns: %d", len(local_patterns))

    spec = extract_spec(product_words, client, model)
    if spec:
        stage2_patterns = build_regex_from_spec(spec)
        logger.info("[generate_regex] Stage 2 patterns: %d", len(stage2_patterns))
    else:
        stage2_patterns = []
        logger.warning("[generate_regex] Stage 1 failed; using local seeds only")

    merged = normalize(_merge_patterns(local_patterns, stage2_patterns))
    logger.info("[generate_regex] Final patterns after normalize: %d", len(merged))
    return merged
