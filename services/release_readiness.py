from __future__ import annotations

import os
from typing import Any

from services.deployment_profile import synthetic_evaluation_enabled


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _check(
    check_id: str,
    category: str,
    level: str,
    ready: bool,
    detail: str,
    remediation: str,
) -> dict[str, str]:
    return {
        "check_id": check_id,
        "category": category,
        "level": level,
        "status": "ready" if ready else "blocked",
        "detail": detail,
        "remediation": "None required." if ready else remediation,
    }


def release_readiness_snapshot() -> dict[str, Any]:
    origins = [item.strip() for item in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if item.strip()]
    hosts = [item.strip() for item in os.getenv("TRUSTED_HOSTS", "").split(",") if item.strip()]
    production_checks = [
        _check("production_environment", "configuration", "production_research", os.getenv("DEPLOYMENT_ENV", "local").strip().lower() == "production", "Deployment environment is explicitly marked production.", "Set DEPLOYMENT_ENV=production in the service environment."),
        _check("authentication", "identity", "production_research", os.getenv("AUTH_MODE", "none").strip().lower() == "oidc", "OIDC authentication is configured.", "Set AUTH_MODE=oidc and configure the institutional identity provider."),
        _check("oidc_issuer", "identity", "production_research", bool(os.getenv("OIDC_ISSUER", "").strip()), "An OIDC token issuer is configured.", "Set OIDC_ISSUER to the exact HTTPS issuer URL."),
        _check("oidc_audience", "identity", "production_research", bool(os.getenv("OIDC_AUDIENCE", "").strip()), "An API audience is configured for token validation.", "Set OIDC_AUDIENCE to the protected API identifier."),
        _check("https_enforcement", "transport", "production_research", _enabled("REQUIRE_HTTPS"), "HTTPS enforcement is enabled.", "Terminate TLS at the trusted edge and set REQUIRE_HTTPS=true."),
        _check("explicit_cors", "network", "production_research", bool(origins) and all("localhost" not in item and "127.0.0.1" not in item for item in origins), "CORS is restricted to explicit non-local origins.", "Set CORS_ALLOWED_ORIGINS to the exact trusted frontend origins."),
        _check("trusted_hosts", "network", "production_research", bool(hosts) and all(item not in {"localhost", "127.0.0.1", "testserver", "*"} for item in hosts), "Trusted hosts are explicit and non-local.", "Set TRUSTED_HOSTS to the deployed API hostnames."),
        _check("external_rate_limiting", "abuse_protection", "production_research", os.getenv("RATE_LIMITING_MODE", "none").strip().lower() not in {"", "none"}, "An external or shared rate-limiting layer is declared.", "Configure shared gateway rate limiting. Do not rely on process-local counters."),
        _check("monitoring_sink", "operations", "production_research", bool(os.getenv("MONITORING_SINK", "").strip()), "A monitoring and alerting destination is configured.", "Configure a governed monitoring sink and alert ownership."),
        _check("backup_policy", "resilience", "production_research", bool(os.getenv("BACKUP_POLICY", "").strip()), "A documented backup and restore policy is configured.", "Define backup frequency, retention, restore testing, and ownership."),
        _check("durable_state_store", "resilience", "production_research", bool(os.getenv("DATABASE_URL", "").strip()), "A durable PostgreSQL case store is configured.", "Set DATABASE_URL to the managed PostgreSQL connection string and test backup restoration."),
    ]
    local_checks = [
        _check(
            "research_boundary",
            "scope",
            "local_research",
            True,
            "The API is restricted to the controlled synthetic teaching case."
            if synthetic_evaluation_enabled()
            else "The API accepts only synthetic or fully de-identified research case types.",
            "",
        ),
        _check("fail_closed_defaults", "safety", "local_research", True, "Evidence and model integrations fail closed when they are unavailable.", ""),
        _check("request_isolation", "runtime", "local_research", True, "Workflow dependencies are created per request.", ""),
        _check("deidentification_screen", "privacy", "local_research", True, "De-identified uploads require attestation and a secondary identifier screen; original files are not retained.", ""),
        _check("deterministic_evaluation", "evaluation", "local_research", True, "Phase 9 governance evaluations are deterministic and inspectable.", ""),
    ]
    clinical_checks = [
        {
            "check_id": "institutional_clinical_governance",
            "category": "clinical_governance",
            "level": "clinical_release",
            "status": "blocked",
            "detail": "Clinical release is not authorized by this research software.",
            "remediation": "Complete institutional privacy, security, regulatory, local validation, prospective or silent evaluation, change control, and accountable clinical governance outside this codebase.",
        }
    ]
    production_ready = all(item["status"] == "ready" for item in production_checks)
    return {
        "overall_state": "production_research_ready" if production_ready else "production_research_blocked",
        "local_research_ready": True,
        "production_research_ready": production_ready,
        "clinical_release_authorized": False,
        "checks": local_checks + production_checks + clinical_checks,
        "boundary": (
            "Passing software checks does not authorize clinical use. Production research and clinical release "
            "require separate operational and institutional decisions."
        ),
    }
