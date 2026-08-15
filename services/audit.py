from __future__ import annotations

from datetime import datetime, timezone


def audit_event(event: str, detail: str = "") -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "detail": detail,
    }
