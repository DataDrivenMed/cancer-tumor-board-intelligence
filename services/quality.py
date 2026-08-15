from __future__ import annotations

from schemas.case import CancerTumorBoardCase, MissingItem, Conflict


def inspect_case(case: CancerTumorBoardCase) -> tuple[list[Conflict], list[MissingItem]]:
    conflicts = list(case.conflicts)
    missing = list(case.missing_items)

    if case.performance_status is None:
        missing.append(MissingItem(
            field="performance_status",
            importance="high",
            reason="Performance status can materially affect treatment tolerability and trial matching.",
            availability="not_documented",
            recommendation_blocking=False,
        ))

    if not case.treatments:
        missing.append(MissingItem(
            field="prior_treatment_history",
            importance="high",
            reason="Treatment sequencing depends on prior exposure and response.",
            availability="not_documented",
            recommendation_blocking=False,
        ))

    return conflicts, missing
