from __future__ import annotations

from qualification.scoring_v24 import score_case_v24

SCORING_V25_VERSION = "2.5.0"


def score_case_v25(gold, package):
    # Deliberately preserve the frozen v2.4 core scoring contract. v2.5 adds
    # stronger semantic-integrity gates rather than weakening qualification.
    return score_case_v24(gold, package)
