import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  ID_COOKIE,
  authenticationRequired,
  decodeIdentityToken,
} from "../../../lib/server-auth";

export async function GET() {
  if (!authenticationRequired()) {
    return NextResponse.json({ authenticated: true, mode: "local", user: { name: "Local product user", organization: "Local workspace" } });
  }
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(ACCESS_COOKIE)?.value;
  const accessClaims = decodeIdentityToken(accessToken);
  const expiresAt = typeof accessClaims.exp === "number" ? accessClaims.exp * 1000 : 0;
  const authenticated = Boolean(accessToken && expiresAt > Date.now());
  const claims = decodeIdentityToken(cookieStore.get(ID_COOKIE)?.value);
  const response = NextResponse.json({
    authenticated,
    mode: "oidc",
    user: authenticated ? {
      id: claims.sub || null,
      name: claims.name || claims.email || "Signed-in user",
      email: claims.email || null,
      organization: claims.org_name || claims.org_id || "Personal workspace",
    } : null,
  }, { headers: { "Cache-Control": "no-store" } });
  if (!authenticated) {
    response.cookies.delete(ACCESS_COOKIE);
    response.cookies.delete(ID_COOKIE);
  }
  return response;
}
