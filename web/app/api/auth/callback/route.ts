import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  ID_COOKIE,
  STATE_COOKIE,
  VERIFIER_COOKIE,
  NONCE_COOKIE,
  applicationBaseUrl,
  decodeIdentityToken,
  oidcMetadata,
  secureCookies,
} from "../../../lib/server-auth";

export async function GET(request: NextRequest) {
  const cookieStore = await cookies();
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const expectedState = cookieStore.get(STATE_COOKIE)?.value;
  const verifier = cookieStore.get(VERIFIER_COOKIE)?.value;
  const expectedNonce = cookieStore.get(NONCE_COOKIE)?.value;
  if (!code || !state || !expectedState || state !== expectedState || !verifier || !expectedNonce) {
    return NextResponse.redirect(`${applicationBaseUrl()}/?auth_error=invalid_callback`);
  }
  try {
    const metadata = await oidcMetadata();
    const values = new URLSearchParams({
      grant_type: "authorization_code",
      client_id: process.env.OIDC_CLIENT_ID || "",
      code,
      code_verifier: verifier,
      redirect_uri: `${applicationBaseUrl()}/api/auth/callback`,
    });
    if (process.env.OIDC_CLIENT_SECRET) values.set("client_secret", process.env.OIDC_CLIENT_SECRET);
    const tokenResponse = await fetch(metadata.token_endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: values,
      cache: "no-store",
    });
    if (!tokenResponse.ok) throw new Error("Token exchange failed.");
    const token = await tokenResponse.json() as {
      access_token: string;
      id_token?: string;
      expires_in?: number;
    };
    if (!token.access_token || !token.id_token) throw new Error("OIDC tokens were incomplete.");
    if (decodeIdentityToken(token.id_token).nonce !== expectedNonce) throw new Error("OIDC nonce validation failed.");
    const maxAge = Math.min(Number(token.expires_in || 3600), 28_800);
    const response = NextResponse.redirect(applicationBaseUrl());
    const options = { httpOnly: true, secure: secureCookies(), sameSite: "lax" as const, path: "/", maxAge };
    response.cookies.set(ACCESS_COOKIE, token.access_token, options);
    if (token.id_token) response.cookies.set(ID_COOKIE, token.id_token, options);
    response.cookies.delete(STATE_COOKIE);
    response.cookies.delete(VERIFIER_COOKIE);
    response.cookies.delete(NONCE_COOKIE);
    return response;
  } catch {
    return NextResponse.redirect(`${applicationBaseUrl()}/?auth_error=identity_provider_unavailable`);
  }
}
