"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    setLoading(false);
    if (res.ok) {
      router.push(params.get("next") || "/");
      router.refresh();
    } else {
      setError("Invalid password");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={submit} className="card w-full max-w-sm">
        <div className="mb-1 text-2xl font-bold text-white">🤠 Slick HQ</div>
        <p className="mb-6 text-sm text-slate-400">Sheriff S command deck — sign in</p>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Admin password"
          className="w-full rounded-lg border border-slick-border bg-slick-bg px-3 py-2 text-slate-200 outline-none focus:border-slick-accent"
          autoFocus
        />
        {error && <p className="mt-2 text-sm text-rose-400">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="mt-4 w-full rounded-lg bg-slick-accent px-4 py-2 font-medium text-slick-bg hover:bg-sky-400 disabled:opacity-60"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
