from __future__ import annotations

from qualification.scoring_v22 import SCORING_V22_VERSION as _BASE_SCORING_VERSION, score_case_v22, summarize

SCORING_V24_VERSION = "2.4.0"


def score_case_v24(gold, package):
    """v2.4 intentionally preserves the strict v2.2 scoring contract unchanged."""
    return score_case_v22(gold, package)


__all__ = ["SCORING_V24_VERSION", "score_case_v24", "summarize"]
