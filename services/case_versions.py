from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4


ALL_SPECIALIST_AGENTS = {
    "guideline",
    "molecular",
    "translational",
    "literature",
    "clinical_trials",
    "safety",
}

ALWAYS_RERUN_CONTROLS = [
    "semantic_integrity",
    "case_integrity",
    "missing_information",
    "routing",
    "clinical_red_team",
    "consensus",
    "tumor_board_brief",
]

FIELD_AGENT_DEPENDENCIES: dict[str, set[str]] = {
    "diagnosis": set(ALL_SPECIALIST_AGENTS),
    "disease_state": set(ALL_SPECIALIST_AGENTS),
    "stage": {"guideline", "literature", "clinical_trials", "safety"},
    "performance_status": {"guideline", "literature", "clinical_trials", "safety"},
    "pathology": {"guideline", "molecular", "translational", "literature", "clinical_trials"},
    "molecular_findings": {"guideline", "molecular", "translational", "literature", "clinical_trials", "safety"},
    "imaging": {"guideline", "literature", "clinical_trials", "safety"},
    "labs": {"guideline", "clinical_trials", "safety"},
    "comorbidities": {"guideline", "clinical_trials", "safety"},
    "treatments": set(ALL_SPECIALIST_AGENTS),
    "toxicities": {"guideline", "literature", "clinical_trials", "safety"},
    "transplant_cellular_therapy": {"guideline", "literature", "clinical_trials", "safety"},
    "current_medications": {"guideline", "clinical_trials", "safety"},
    "clinical_question": set(ALL_SPECIALIST_AGENTS),
    "care_site": {"clinical_trials"},
    "age": {"guideline", "literature", "clinical_trials", "safety"},
    "sex": {"guideline", "literature", "clinical_trials", "safety"},
    "source_documents": set(),
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _decode(value: Any) -> Any:
    if value is None:
        return None
    return json.loads(value) if isinstance(value, str) else value


def _changed_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    if type(before) is not type(after):
        return [prefix or "$case"]
    if isinstance(before, dict):
        paths: list[str] = []
        for key in sorted(set(before) | set(after)):
            child = f"{prefix}.{key}" if prefix else key
            if key not in before or key not in after:
                paths.append(child)
            else:
                paths.extend(_changed_paths(before[key], after[key], child))
        return paths
    if isinstance(before, list):
        if before == after:
            return []
        return [prefix]
    return [] if before == after else [prefix]


def assess_case_update(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    if before.get("case_id") != after.get("case_id"):
        raise ValueError("An update cannot change the canonical case identifier.")
    if before.get("case_type") != after.get("case_type"):
        raise ValueError("An update cannot change the governed case type.")

    changed_paths = _changed_paths(before, after)
    if not changed_paths:
        raise ValueError("The proposed case contains no changes from the selected base version.")

    changed_roots = sorted({path.split(".", 1)[0] for path in changed_paths})
    rerun_agents: set[str] = set()
    for root in changed_roots:
        rerun_agents.update(FIELD_AGENT_DEPENDENCIES.get(root, ALL_SPECIALIST_AGENTS))

    decision_critical_roots = {
        "diagnosis",
        "disease_state",
        "stage",
        "performance_status",
        "pathology",
        "molecular_findings",
        "treatments",
        "toxicities",
        "clinical_question",
    }
    severity = "decision_critical" if decision_critical_roots.intersection(changed_roots) else "workflow_relevant"
    return {
        "changed_paths": changed_paths,
        "changed_roots": changed_roots,
        "change_severity": severity,
        "specialist_agents_to_rerun": sorted(rerun_agents),
        "specialist_agents_eligible_for_reuse": sorted(ALL_SPECIALIST_AGENTS - rerun_agents),
        "always_rerun_controls": list(ALWAYS_RERUN_CONTROLS),
        "evidence_review_required": True,
        "prior_decision_status": "historical_only",
        "explanation": (
            "Every deterministic safety gate and final synthesis step will run again. "
            "Only specialist outputs outside the changed field dependency set may be reused."
        ),
    }


class SQLiteCaseVersionStore:
    """Append-only local storage for immutable governed case snapshots."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @classmethod
    def from_environment(cls) -> "SQLiteCaseVersionStore":
        configured = os.getenv("TUMOR_BOARD_STATE_DB", "").strip()
        default = Path(__file__).resolve().parents[1] / ".local" / "tumor_board_state.sqlite3"
        return cls(configured or default)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS product_case_versions (
                    version_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    parent_version_id TEXT,
                    created_at TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    change_summary TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    case_json TEXT NOT NULL,
                    raw_extraction_json TEXT,
                    workflow_json TEXT NOT NULL,
                    evidence_review_json TEXT NOT NULL,
                    human_decision_json TEXT NOT NULL,
                    FOREIGN KEY(parent_version_id) REFERENCES product_case_versions(version_id),
                    UNIQUE(organization_id, case_id, version_number),
                    UNIQUE(organization_id, case_id, content_hash)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS product_case_versions_tenant_case_idx "
                "ON product_case_versions(organization_id, case_id, version_number DESC)"
            )
            legacy = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='case_versions'"
            ).fetchone()
            if legacy:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO product_case_versions (
                        version_id, organization_id, created_by, case_id, version_number,
                        parent_version_id, created_at, trigger, change_summary, content_hash,
                        case_json, raw_extraction_json, workflow_json, evidence_review_json,
                        human_decision_json
                    )
                    SELECT version_id, 'local-workspace', 'legacy-local-user', case_id,
                        version_number, parent_version_id, created_at, trigger, change_summary,
                        content_hash, case_json, raw_extraction_json, workflow_json,
                        evidence_review_json, human_decision_json
                    FROM case_versions
                    """
                )

    def save_version(
        self,
        *,
        case: dict[str, Any],
        raw_extraction: dict[str, Any] | None,
        workflow: dict[str, Any],
        evidence_review: dict[str, Any],
        human_decision: dict[str, Any],
        parent_version_id: str | None,
        trigger: str,
        change_summary: str,
        organization_id: str = "local-workspace",
        created_by: str = "local-user",
    ) -> tuple[dict[str, Any], bool]:
        case_id = str(case.get("case_id") or "")
        if not case_id:
            raise ValueError("A canonical case identifier is required.")
        if workflow.get("case_id") != case_id:
            raise ValueError("The workflow result does not belong to the submitted case.")
        if human_decision.get("case_id") != case_id:
            raise ValueError("The human decision receipt does not belong to the submitted case.")
        if human_decision.get("workflow_request_id") != workflow.get("request_id"):
            raise ValueError("The human decision receipt does not reference the submitted workflow run.")
        final_decision = (workflow.get("result") or {}).get("final_decision")
        if human_decision.get("system_decision") != final_decision:
            raise ValueError("The human decision receipt does not preserve the submitted workflow decision.")

        snapshot = {
            "case": case,
            "raw_extraction": raw_extraction,
            "workflow": workflow,
            "evidence_review": evidence_review,
            "human_decision": human_decision,
        }
        content_hash = hashlib.sha256(_canonical(snapshot).encode("utf-8")).hexdigest()
        created_at = datetime.now(UTC).isoformat()

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if parent_version_id:
                parent = connection.execute(
                    "SELECT case_id FROM product_case_versions WHERE version_id = ? AND organization_id = ?",
                    (parent_version_id, organization_id),
                ).fetchone()
                if not parent or parent["case_id"] != case_id:
                    raise ValueError("The selected parent version does not belong to this case.")

            existing = connection.execute(
                "SELECT * FROM product_case_versions WHERE organization_id = ? AND case_id = ? AND content_hash = ?",
                (organization_id, case_id, content_hash),
            ).fetchone()
            if existing:
                connection.commit()
                return self._row_to_detail(existing), False

            version_number = int(
                connection.execute(
                    "SELECT COALESCE(MAX(version_number), 0) + 1 FROM product_case_versions WHERE organization_id = ? AND case_id = ?",
                    (organization_id, case_id),
                ).fetchone()[0]
            )
            version_id = f"cv_{uuid4().hex}"
            connection.execute(
                """
                INSERT INTO product_case_versions (
                    version_id, organization_id, created_by, case_id, version_number, parent_version_id, created_at,
                    trigger, change_summary, content_hash, case_json, raw_extraction_json,
                    workflow_json, evidence_review_json, human_decision_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    organization_id,
                    created_by,
                    case_id,
                    version_number,
                    parent_version_id,
                    created_at,
                    trigger,
                    change_summary.strip(),
                    content_hash,
                    _json(case),
                    _json(raw_extraction) if raw_extraction is not None else None,
                    _json(workflow),
                    _json(evidence_review),
                    _json(human_decision),
                ),
            )
            row = connection.execute(
                "SELECT * FROM product_case_versions WHERE version_id = ? AND organization_id = ?",
                (version_id, organization_id),
            ).fetchone()
            connection.commit()
        return self._row_to_detail(row), True

    def list_versions(self, case_id: str, *, organization_id: str = "local-workspace") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM product_case_versions WHERE organization_id = ? AND case_id = ? ORDER BY version_number DESC",
                (organization_id, case_id),
            ).fetchall()
        return [self._row_to_summary(row) for row in rows]

    def list_all_versions(self, *, organization_id: str = "local-workspace") -> list[dict[str, Any]]:
        """Return complete snapshots for deterministic release evaluation."""

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM product_case_versions WHERE organization_id = ? ORDER BY created_at DESC, version_number DESC",
                (organization_id,),
            ).fetchall()
        return [self._row_to_detail(row) for row in rows]

    def list_cases(self, *, organization_id: str = "local-workspace") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT current.* FROM product_case_versions current
                JOIN (
                    SELECT case_id, MAX(version_number) AS latest_version
                    FROM product_case_versions WHERE organization_id = ? GROUP BY case_id
                ) latest ON latest.case_id = current.case_id AND latest.latest_version = current.version_number
                WHERE current.organization_id = ? ORDER BY current.created_at DESC
                """,
                (organization_id, organization_id),
            ).fetchall()
        return [self._row_to_summary(row) for row in rows]

    def get_version(
        self,
        version_id: str,
        *,
        case_id: str | None = None,
        organization_id: str = "local-workspace",
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM product_case_versions WHERE version_id = ? AND organization_id = ?",
                (version_id, organization_id),
            ).fetchone()
        if not row or (case_id is not None and row["case_id"] != case_id):
            return None
        return self._row_to_detail(row)

    @staticmethod
    def _row_to_summary(row: Any) -> dict[str, Any]:
        workflow = _decode(row["workflow_json"]) or {}
        human = _decode(row["human_decision_json"]) or {}
        final = (workflow.get("result") or {}).get("final_decision") or {}
        return {
            "version_id": row["version_id"],
            "organization_id": row["organization_id"],
            "created_by": row["created_by"],
            "case_id": row["case_id"],
            "version_number": row["version_number"],
            "parent_version_id": row["parent_version_id"],
            "created_at": row["created_at"],
            "trigger": row["trigger"],
            "change_summary": row["change_summary"],
            "content_hash": row["content_hash"],
            "workflow_request_id": workflow.get("request_id", ""),
            "decision_record_id": human.get("decision_record_id", ""),
            "decision_state": final.get("decision_state", "unknown"),
            "board_status": (human.get("board_decision") or {}).get("status", "unknown"),
        }

    @classmethod
    def _row_to_detail(cls, row: Any) -> dict[str, Any]:
        return {
            **cls._row_to_summary(row),
            "case": _decode(row["case_json"]),
            "raw_extraction": _decode(row["raw_extraction_json"]),
            "workflow": _decode(row["workflow_json"]),
            "evidence_review": _decode(row["evidence_review_json"]),
            "human_decision": _decode(row["human_decision_json"]),
        }


class PostgresCaseVersionStore(SQLiteCaseVersionStore):
    """Tenant-isolated PostgreSQL storage for production case versions."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._initialize()

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS product_case_versions (
                    version_id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    parent_version_id TEXT REFERENCES product_case_versions(version_id),
                    created_at TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    change_summary TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    case_json TEXT NOT NULL,
                    raw_extraction_json TEXT,
                    workflow_json TEXT NOT NULL,
                    evidence_review_json TEXT NOT NULL,
                    human_decision_json TEXT NOT NULL,
                    UNIQUE(organization_id, case_id, version_number),
                    UNIQUE(organization_id, case_id, content_hash)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS product_case_versions_tenant_case_idx "
                "ON product_case_versions(organization_id, case_id, version_number DESC)"
            )

    def save_version(self, **values: Any) -> tuple[dict[str, Any], bool]:
        case = values["case"]
        workflow = values["workflow"]
        human_decision = values["human_decision"]
        evidence_review = values["evidence_review"]
        raw_extraction = values.get("raw_extraction")
        parent_version_id = values.get("parent_version_id")
        organization_id = values.get("organization_id", "local-workspace")
        created_by = values.get("created_by", "local-user")
        case_id = str(case.get("case_id") or "")
        if not case_id:
            raise ValueError("A canonical case identifier is required.")
        if workflow.get("case_id") != case_id or human_decision.get("case_id") != case_id:
            raise ValueError("The submitted governed package does not belong to this case.")
        if human_decision.get("workflow_request_id") != workflow.get("request_id"):
            raise ValueError("The human decision receipt does not reference the submitted workflow run.")
        if human_decision.get("system_decision") != (workflow.get("result") or {}).get("final_decision"):
            raise ValueError("The human decision receipt does not preserve the submitted workflow decision.")
        snapshot = {
            "case": case,
            "raw_extraction": raw_extraction,
            "workflow": workflow,
            "evidence_review": evidence_review,
            "human_decision": human_decision,
        }
        content_hash = hashlib.sha256(_canonical(snapshot).encode("utf-8")).hexdigest()
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (f"{organization_id}:{case_id}",),
            )
            if parent_version_id:
                parent = connection.execute(
                    "SELECT case_id FROM product_case_versions WHERE version_id = %s AND organization_id = %s",
                    (parent_version_id, organization_id),
                ).fetchone()
                if not parent or parent["case_id"] != case_id:
                    raise ValueError("The selected parent version does not belong to this case.")
            existing = connection.execute(
                "SELECT * FROM product_case_versions WHERE organization_id = %s AND case_id = %s AND content_hash = %s",
                (organization_id, case_id, content_hash),
            ).fetchone()
            if existing:
                return self._row_to_detail(existing), False
            version_number = int(connection.execute(
                "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_version FROM product_case_versions WHERE organization_id = %s AND case_id = %s",
                (organization_id, case_id),
            ).fetchone()["next_version"])
            version_id = f"cv_{uuid4().hex}"
            connection.execute(
                """
                INSERT INTO product_case_versions (
                    version_id, organization_id, created_by, case_id, version_number,
                    parent_version_id, created_at, trigger, change_summary, content_hash,
                    case_json, raw_extraction_json, workflow_json, evidence_review_json,
                    human_decision_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    version_id, organization_id, created_by, case_id, version_number,
                    parent_version_id, created_at, values["trigger"], values["change_summary"].strip(),
                    content_hash, _json(case), _json(raw_extraction) if raw_extraction is not None else None,
                    _json(workflow), _json(evidence_review), _json(human_decision),
                ),
            )
            row = connection.execute(
                "SELECT * FROM product_case_versions WHERE version_id = %s AND organization_id = %s",
                (version_id, organization_id),
            ).fetchone()
        return self._row_to_detail(row), True

    def list_versions(self, case_id: str, *, organization_id: str = "local-workspace") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM product_case_versions WHERE organization_id = %s AND case_id = %s ORDER BY version_number DESC",
                (organization_id, case_id),
            ).fetchall()
        return [self._row_to_summary(row) for row in rows]

    def list_all_versions(self, *, organization_id: str = "local-workspace") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM product_case_versions WHERE organization_id = %s ORDER BY created_at DESC, version_number DESC",
                (organization_id,),
            ).fetchall()
        return [self._row_to_detail(row) for row in rows]

    def list_cases(self, *, organization_id: str = "local-workspace") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT ON (case_id) * FROM product_case_versions
                WHERE organization_id = %s ORDER BY case_id, version_number DESC
                """,
                (organization_id,),
            ).fetchall()
        return [self._row_to_summary(row) for row in sorted(rows, key=lambda item: item["created_at"], reverse=True)]

    def get_version(self, version_id: str, *, case_id: str | None = None, organization_id: str = "local-workspace") -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM product_case_versions WHERE version_id = %s AND organization_id = %s",
                (version_id, organization_id),
            ).fetchone()
        if not row or (case_id is not None and row["case_id"] != case_id):
            return None
        return self._row_to_detail(row)


@lru_cache(maxsize=8)
def _configured_case_version_store(
    database_url: str,
    sqlite_path: str,
) -> SQLiteCaseVersionStore:
    if database_url:
        return PostgresCaseVersionStore(database_url)
    if sqlite_path:
        return SQLiteCaseVersionStore(sqlite_path)
    default = Path(__file__).resolve().parents[1] / ".local" / "tumor_board_state.sqlite3"
    return SQLiteCaseVersionStore(default)


def case_version_store_from_environment() -> SQLiteCaseVersionStore:
    return _configured_case_version_store(
        os.getenv("DATABASE_URL", "").strip(),
        os.getenv("TUMOR_BOARD_STATE_DB", "").strip(),
    )


def evidence_changed_agents(
    previous_review: dict[str, Any],
    current_decisions: Iterable[dict[str, Any]],
) -> set[str]:
    previous = {
        str(item.get("candidate_id")): (item.get("decision"), item.get("reason", ""))
        for item in previous_review.get("decisions", [])
    }
    current = {
        str(item.get("candidate_id")): (item.get("decision"), item.get("reason", ""))
        for item in current_decisions
    }
    changed_ids = set(previous) | set(current)
    changed_ids = {candidate_id for candidate_id in changed_ids if previous.get(candidate_id) != current.get(candidate_id)}
    agents: set[str] = set()
    for candidate_id in changed_ids:
        channel = candidate_id.split(":", 1)[0]
        if channel in {"guideline", "molecular", "safety"}:
            agents.add(channel)
    return agents
