from __future__ import annotations

from qualification.cases import GoldCase
from qualification.scoring import QualificationScore, summarize
from qualification.scoring_v22 import score_case_v22


SCORING_V23_VERSION = "2.3.0"


def score_case_v23(gold: GoldCase, package) -> QualificationScore:
    """v2.3 keeps the frozen v2.2 strict scoring contract.

    Remediation is performed in extraction/canonicalization, not by weakening the
    evaluator. This wrapper exists so the v2.3 fingerprint explicitly versions the
    scoring layer while preserving the same strict gates.
    """
    return score_case_v22(gold, package)


__all__ = ["SCORING_V23_VERSION", "score_case_v23", "summarize"]
