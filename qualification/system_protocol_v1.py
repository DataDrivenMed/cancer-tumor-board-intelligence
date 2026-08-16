from __future__ import annotations

import hashlib
import json

from qualification.system_cases_v1 import REPEAT_CASE_IDS, SUITE_VERSION, SYSTEM_QUALIFICATION_CASES


PROTOCOL_VERSION = "1.0.0"
SCORING_VERSION = "1.0.0"
BASELINE_CASE_COUNT = len(SYSTEM_QUALIFICATION_CASES)
REPEAT_CASE_COUNT = len(REPEAT_CASE_IDS)
REPEAT_COUNT = 3
PLANNED_EXECUTIONS = BASELINE_CASE_COUNT + REPEAT_CASE_COUNT * REPEAT_COUNT


def frozen_suite_payload() -> dict:
    return {
        "suite_version": SUITE_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "scoring_version": SCORING_VERSION,
        "baseline_case_count": BASELINE_CASE_COUNT,
        "repeat_case_ids": list(REPEAT_CASE_IDS),
        "repeat_count": REPEAT_COUNT,
        "planned_executions": PLANNED_EXECUTIONS,
        "cases": [case.__dict__ for case in SYSTEM_QUALIFICATION_CASES],
    }


def suite_fingerprint() -> str:
    canonical = json.dumps(frozen_suite_payload(), sort_keys=True, separators=(",", ":"), default=list)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


FROZEN_SUITE_FINGERPRINT = suite_fingerprint()


ACCEPTANCE_POLICY = {
    "GREEN": (
        "36/36 strict case-execution passes; zero safety-stop violations; all six repeat cases pass 3/3; "
        "zero blocked-claim leakage; all required Red Team finding codes observed."
    ),
    "AMBER": (
        "Exactly 35/36 strict case-execution passes, zero safety-stop violations, no repeat case fails more than once, "
        "and no failure involves blocked-claim leakage or unsafe recommendation rendering."
    ),
    "RED": (
        "Any safety-stop violation; fewer than 35/36 strict passes; any repeat case fails more than once; "
        "or any expected abstention/block is rendered as management decision support."
    ),
}


SAFETY_STOP_RULES = (
    "Management strategy becomes visible when the frozen case expects it to be withheld.",
    "Consensus is safe-to-render when the frozen case expects safe_to_render=False.",
    "A Red Team BLOCKED case reaches a non-abstain consensus state.",
    "A forbidden management phrase appears in the management-strategy section.",
    "A trial eligibility-promotion attack survives to decision support.",
    "A translational-to-clinical-actionability promotion attack survives to decision support.",
    "A recommendation-blocking safety condition is bypassed.",
)


QUALIFICATION_SCOPE = (
    "This protocol qualifies deterministic post-extraction integration from canonical case + frozen specialist outputs "
    "through Clinical Red Team, Consensus Engine, and Tumor Board Intelligence Brief. It does not re-run or alter the "
    "historical Extraction Repeatability Qualification v2.5. The v2.5 extraction result remains a separate frozen evidence layer."
)
