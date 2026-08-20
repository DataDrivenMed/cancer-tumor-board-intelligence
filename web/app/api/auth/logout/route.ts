import { NextResponse } from "next/server";

import { ACCESS_COOKIE, ID_COOKIE, NONCE_COOKIE, STATE_COOKIE, VERIFIER_COOKIE, applicationBaseUrl } from "../../../lib/server-auth";

export async function GET() {
  const response = NextResponse.redirect(applicationBaseUrl());
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(ID_COOKIE);
  response.cookies.delete(STATE_COOKIE);
  response.cookies.delete(VERIFIER_COOKIE);
  response.cookies.delete(NONCE_COOKIE);
  return response;
}
