import "server-only";

import { createHash, randomBytes } from "node:crypto";

export const ACCESS_COOKIE = "tbi_access";
export const ID_COOKIE = "tbi_identity";
export const STATE_COOKIE = "tbi_oauth_state";
export const VERIFIER_COOKIE = "tbi_oauth_verifier";
export const NONCE_COOKIE = "tbi_oauth_nonce";

export function authenticationRequired(): boolean {
  return process.env.NEXT_PUBLIC_AUTH_MODE === "oidc";
}

export function applicationBaseUrl(): string {
  return (process.env.APP_BASE_URL || "http://localhost:3000").replace(/\/$/, "");
}

export function secureCookies(): boolean {
  return applicationBaseUrl().startsWith("https://");
}

export function randomUrlToken(bytes = 32): string {
  return randomBytes(bytes).toString("base64url");
}

export function codeChallenge(verifier: string): string {
  return createHash("sha256").update(verifier).digest("base64url");
}

export async function oidcMetadata(): Promise<Record<string, string>> {
  const issuer = (process.env.OIDC_ISSUER || "").replace(/\/$/, "");
  if (!issuer) throw new Error("OIDC_ISSUER is not configured.");
  const response = await fetch(`${issuer}/.well-known/openid-configuration`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("The identity provider metadata could not be loaded.");
  return (await response.json()) as Record<string, string>;
}

export function decodeIdentityToken(token: string | undefined): Record<string, unknown> {
  if (!token) return {};
  try {
    const payload = token.split(".")[1];
    return JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as Record<string, unknown>;
  } catch {
    return {};
  }
}
