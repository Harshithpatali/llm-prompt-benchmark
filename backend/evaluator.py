"""Reference-overlap diagnostics for general LLM responses.

These are lexical triage signals only. They are not semantic correctness,
factuality, safety, or groundedness measurements.
"""
from __future__ import annotations

import re

STOP_WORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "is", "are", "for",
    "with", "on", "by", "as", "be", "this", "that", "it", "you", "your",
    "we", "our", "can", "will", "from", "at", "if", "not", "only", "use",
}


def terms(text: str) -> set[str]:
    """Return normalized content tokens using set-based overlap."""
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").casefold())
        if len(token) > 2 and token not in STOP_WORDS
    }


def evaluate_reference_overlap(response: str, reference: str) -> dict:
    """Calculate interpretable lexical diagnostics against a reference answer."""
    reference_terms = terms(reference)
    response_terms = terms(response)
    matched = reference_terms & response_terms

    precision = len(matched) / len(response_terms) if response_terms else 0.0
    recall = len(matched) / len(reference_terms) if reference_terms else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )

    response_length = len((response or "").split())
    reference_length = max(len((reference or "").split()), 1)
    length_ratio = min(response_length / reference_length, 1.0)
    length_sanity = min(length_ratio / 0.45, 1.0)
    heuristic_score = round(100 * (0.8 * f1 + 0.2 * length_sanity), 2)

    return {
        "keyword_precision": round(precision, 4),
        "keyword_recall": round(recall, 4),
        "keyword_f1": round(f1, 4),
        "keyword_coverage": round(recall, 4),
        "length_sanity": round(length_sanity, 4),
        "heuristic_score": heuristic_score,
        "matched_terms": sorted(matched),
        "missing_terms": sorted(reference_terms - response_terms),
        "extra_terms": sorted(response_terms - reference_terms),
        "method": "deterministic_reference_overlap_v2",
        "interpretation": (
            "Lexical overlap diagnostic only; not semantic correctness, "
            "factuality, relevance, groundedness, or safety."
        ),
    }
