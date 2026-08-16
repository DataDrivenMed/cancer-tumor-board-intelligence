from __future__ import annotations

from dataclasses import dataclass
import re

from schemas.case import DataStatus, Fact, InformationType, Provenance
from services.document_parser import ParsedDocument


# This pattern recognizes only an explicitly written stage label. It intentionally
# does not derive a stage from TNM, imaging, pathology, biomarkers, or disease extent.
_STAGE_RE = re.compile(
    r"\b(?:(?:clinical|pathologic|pathological|anatomic|prognostic|ajcc|figo|ann\s+arbor|r-iss|iss)\s+)?"
    r"stage\s+(?P<label>0|[1-4](?:[abc])?(?:[1-3])?|[ivx]{1,4}(?:[abc])?(?:[1-3])?)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ExplicitStageResult:
    fact: Fact | None
    warnings: tuple[str, ...] = ()
    candidate_count: int = 0


def _canonical_label(label: str) -> str:
    raw = label.strip().upper()
    roman_to_arabic = {"I": "1", "II": "2", "III": "3", "IV": "4"}
    for roman in ("IV", "III", "II", "I"):
        if raw.startswith(roman):
            return roman_to_arabic[roman] + raw[len(roman):]
    return raw


def extract_explicit_stage(document: ParsedDocument) -> ExplicitStageResult:
    """Extract an explicitly stated stage phrase with exact source provenance.

    If multiple different stage labels are present, no canonical value is selected.
    The returned fact is marked conflicting so downstream review can request temporal
    or source reconciliation rather than guessing which stage is current.
    """
    matches: list[tuple[str, str, str, int | None]] = []
    for segment in document.segments:
        for match in _STAGE_RE.finditer(segment.text):
            excerpt = match.group(0)
            canonical = _canonical_label(match.group("label"))
            matches.append((canonical, excerpt, segment.segment_id, segment.page))

    if not matches:
        return ExplicitStageResult(fact=None, candidate_count=0)

    unique_labels = list(dict.fromkeys(item[0] for item in matches))
    provenances = [
        Provenance(
            document_id=document.document_id,
            document_type=document.document_type,
            source_excerpt=excerpt,
            source_segment_ids=[segment_id],
            source_verified=True,
            page=page,
        )
        for _, excerpt, segment_id, page in matches
    ]

    if len(unique_labels) > 1:
        return ExplicitStageResult(
            fact=Fact(
                field="stage",
                value=None,
                status=DataStatus.CONFLICTING,
                information_type=InformationType.OBSERVED,
                provenance=provenances,
                confidence=1.0,
                human_verified=False,
            ),
            warnings=(
                "Multiple distinct explicit stage labels were found. Canonical stage was withheld pending source/temporal reconciliation.",
            ),
            candidate_count=len(matches),
        )

    # Preserve the exact phrase as the patient-facing fact value. The canonical label
    # is used only to determine whether multiple source phrases disagree.
    first = matches[0]
    return ExplicitStageResult(
        fact=Fact(
            field="stage",
            value=first[1],
            status=DataStatus.CONFIRMED,
            information_type=InformationType.OBSERVED,
            provenance=[provenances[0]],
            confidence=1.0,
            human_verified=False,
        ),
        candidate_count=len(matches),
    )
