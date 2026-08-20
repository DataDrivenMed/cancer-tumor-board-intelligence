import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import { ACCESS_COOKIE, authenticationRequired } from "../../../lib/server-auth";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: RouteContext) {
  const backend = (process.env.TUMOR_BOARD_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  const { path } = await context.params;
  const target = new URL(`${backend}/${path.join("/")}`);
  request.nextUrl.searchParams.forEach((value, key) => target.searchParams.append(key, value));

  if (!["GET", "HEAD", "OPTIONS"].includes(request.method)) {
    const origin = request.headers.get("origin");
    if (origin && new URL(origin).host !== request.nextUrl.host) {
      return NextResponse.json({ detail: "Cross-site mutation requests are not allowed." }, { status: 403 });
    }
  }

  const cookieStore = await cookies();
  const accessToken = cookieStore.get(ACCESS_COOKIE)?.value;
  if (authenticationRequired() && !accessToken) {
    return NextResponse.json({ detail: "Sign in is required." }, { status: 401 });
  }
  const headers = new Headers();
  headers.set("Content-Type", request.headers.get("content-type") || "application/json");
  headers.set("X-Request-ID", request.headers.get("x-request-id") || crypto.randomUUID());
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(25_000),
    });
  } catch {
    return NextResponse.json(
      { detail: "The clinical service did not respond in time." },
      { status: 504, headers: { "Cache-Control": "no-store" } },
    );
  }
  const responseHeaders = new Headers();
  responseHeaders.set("Content-Type", upstream.headers.get("content-type") || "application/json");
  responseHeaders.set("Cache-Control", "no-store");
  const requestId = upstream.headers.get("x-request-id");
  if (requestId) responseHeaders.set("X-Request-ID", requestId);
  return new NextResponse(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
