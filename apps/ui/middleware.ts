import { NextRequest, NextResponse } from "next/server";

// v1 auth: a single shared password gate (no user database).
// Pages require the `slick_auth` cookie; /login and /api/login are public.
const PUBLIC_PATHS = ["/login", "/api/login"];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }
  const authed = req.cookies.get("slick_auth")?.value === "ok";
  if (!authed) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  // Protect everything except static assets.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
