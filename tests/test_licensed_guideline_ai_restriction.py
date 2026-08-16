from datetime import date

import pytest

from services.licensed_guideline_adapter import (
    LicensedGuidelineMetadata,
    SourceUseProhibitedError,
    build_licensed_guideline_store,
)


def _metadata() -> LicensedGuidelineMetadata:
    return LicensedGuidelineMetadata(
        source_id="TEST-GUIDE-001",
        title="Test Guideline",
        organization="Test Organization",
        jurisdiction="US",
        version="1.0",
        accessed_date=date(2026, 8, 16),
    )


def test_rejects_source_that_explicitly_prohibits_ai_use() -> None:
    text = (
        "Example guideline text. PLEASE NOTE that use of this Content is governed by the End-User License Agreement, "
        "and you MAY NOT distribute this Content or use it with any artificial intelligence model or tool."
    )

    with pytest.raises(SourceUseProhibitedError):
        build_licensed_guideline_store(
            source_text=text,
            metadata=_metadata(),
            attestations=[],
        )


def test_does_not_reject_source_without_ai_prohibition() -> None:
    store = build_licensed_guideline_store(
        source_text="Authorized guideline source text for deterministic unit testing.",
        metadata=_metadata(),
        attestations=[],
    )
    assert len(store.sources) == 1
    assert store.sources[0].source_id == "TEST-GUIDE-001"
