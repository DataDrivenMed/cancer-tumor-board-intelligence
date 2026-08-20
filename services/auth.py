from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: str
    organization_id: str
    role: str
    email: str | None = None


class AuthenticationError(ValueError):
    pass


def auth_mode() -> str:
    return os.getenv("AUTH_MODE", "none").strip().lower()


@lru_cache(maxsize=4)
def _jwks_client(url: str):
    import jwt

    return jwt.PyJWKClient(url, cache_keys=True, lifespan=300)


@lru_cache(maxsize=4)
def _discovered_jwks_url(issuer: str) -> str:
    import httpx

    try:
        response = httpx.get(
            f"{issuer}/.well-known/openid-configuration",
            timeout=5.0,
            follow_redirects=False,
        )
        response.raise_for_status()
        value = str(response.json().get("jwks_uri") or "")
    except Exception as exc:
        raise AuthenticationError("The OIDC discovery document could not be verified.") from exc
    if not value.startswith("https://"):
        raise AuthenticationError("The OIDC discovery document did not provide an HTTPS JWKS URL.")
    return value


def _organization_claim(claims: dict[str, Any]) -> tuple[str, str]:
    configured_org_claim = os.getenv("OIDC_ORGANIZATION_CLAIM", "").strip()
    configured_role_claim = os.getenv("OIDC_ROLE_CLAIM", "").strip()
    if configured_org_claim and claims.get(configured_org_claim):
        role = claims.get(configured_role_claim) if configured_role_claim else None
        return str(claims[configured_org_claim]), str(role or "member")
    organization = claims.get("o")
    if isinstance(organization, dict) and organization.get("id"):
        return str(organization["id"]), str(organization.get("rol") or "member")
    organization_id = claims.get("org_id")
    organization_role = claims.get("org_role")
    if organization_id:
        return str(organization_id), str(organization_role or "member")
    tenant_id = claims.get("tid")
    if tenant_id:
        return str(tenant_id), "member"
    user_id = str(claims.get("sub") or "")
    return f"personal:{user_id}", "owner"


def authenticate_authorization_header(value: str | None) -> AuthenticatedPrincipal:
    """Verify an OIDC bearer token and return its tenant boundary."""

    if auth_mode() == "none":
        return AuthenticatedPrincipal(
            user_id="local-user",
            organization_id="local-workspace",
            role="owner",
            email="local@example.invalid",
        )

    if auth_mode() != "oidc":
        raise AuthenticationError("AUTH_MODE must be either none or oidc.")
    if not value or not value.startswith("Bearer "):
        raise AuthenticationError("A bearer access token is required.")
    token = value.removeprefix("Bearer ").strip()
    if not token:
        raise AuthenticationError("A bearer access token is required.")

    issuer = os.getenv("OIDC_ISSUER", "").strip().rstrip("/")
    audience = os.getenv("OIDC_AUDIENCE", "").strip()
    if not issuer:
        raise AuthenticationError("OIDC issuer configuration is required.")
    jwks_url = os.getenv("OIDC_JWKS_URL", "").strip() or _discovered_jwks_url(issuer)
    if not jwks_url.startswith("https://"):
        raise AuthenticationError("The OIDC JWKS URL must use HTTPS.")

    try:
        import jwt

        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        decode_options: dict[str, Any] = {
            "key": signing_key.key,
            "algorithms": ["RS256"],
            "issuer": issuer,
        }
        if audience:
            decode_options["audience"] = audience
        else:
            decode_options["options"] = {"verify_aud": False}
        claims = jwt.decode(token, **decode_options)
    except Exception as exc:
        raise AuthenticationError("The access token is invalid or expired.") from exc

    user_id = str(claims.get("sub") or "")
    if not user_id:
        raise AuthenticationError("The access token does not identify a user.")
    organization_id, role = _organization_claim(claims)
    return AuthenticatedPrincipal(
        user_id=user_id,
        organization_id=organization_id,
        role=role,
        email=str(claims.get("email")) if claims.get("email") else None,
    )
