import { NextResponse } from "next/server";

import {
  STATE_COOKIE,
  VERIFIER_COOKIE,
  NONCE_COOKIE,
  applicationBaseUrl,
  authenticationRequired,
  codeChallenge,
  oidcMetadata,
  randomUrlToken,
  secureCookies,
} from "../../../lib/server-auth";

export async function GET() {
  if (!authenticationRequired()) return NextResponse.redirect(applicationBaseUrl());
  const clientId = process.env.OIDC_CLIENT_ID || "";
  if (!clientId) return NextResponse.json({ detail: "OIDC_CLIENT_ID is not configured." }, { status: 503 });
  const metadata = await oidcMetadata();
  const state = randomUrlToken();
  const verifier = randomUrlToken(48);
  const nonce = randomUrlToken();
  const authorization = new URL(metadata.authorization_endpoint);
  authorization.searchParams.set("response_type", "code");
  authorization.searchParams.set("client_id", clientId);
  authorization.searchParams.set("redirect_uri", `${applicationBaseUrl()}/api/auth/callback`);
  authorization.searchParams.set("scope", "openid profile email");
  authorization.searchParams.set("state", state);
  authorization.searchParams.set("nonce", nonce);
  authorization.searchParams.set("code_challenge", codeChallenge(verifier));
  authorization.searchParams.set("code_challenge_method", "S256");
  if (process.env.OIDC_AUDIENCE) authorization.searchParams.set("audience", process.env.OIDC_AUDIENCE);
  const response = NextResponse.redirect(authorization);
  const cookieOptions = { httpOnly: true, secure: secureCookies(), sameSite: "lax" as const, path: "/", maxAge: 600 };
  response.cookies.set(STATE_COOKIE, state, cookieOptions);
  response.cookies.set(VERIFIER_COOKIE, verifier, cookieOptions);
  response.cookies.set(NONCE_COOKIE, nonce, cookieOptions);
  return response;
}
