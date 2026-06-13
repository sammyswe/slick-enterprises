import { NextRequest, NextResponse } from "next/server";

// Compares the submitted password to UI_ADMIN_PASSWORD (server-side env) and sets an
// httpOnly cookie. v1 single-password auth — no user database.
export async function POST(req: NextRequest) {
  const { password } = await req.json().catch(() => ({ password: "" }));
  const expected = process.env.UI_ADMIN_PASSWORD ?? "change-me-please";

  if (!password || password !== expected) {
    return NextResponse.json({ ok: false, error: "Invalid password" }, { status: 401 });
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.set("slick_auth", "ok", {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return res;
}
