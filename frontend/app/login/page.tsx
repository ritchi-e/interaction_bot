"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button, Card, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialMode = searchParams.get("mode") === "register" ? "register" : "login";
  const [mode, setMode] = useState<"login" | "register">(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organisationName, setOrganisationName] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const path = mode === "login" ? "/api/auth/login/" : "/api/auth/register/";
      const body =
        mode === "login" ? { email, password } : { email, password, organisation_name: organisationName };
      const result = await api<{ token: string }>(path, { method: "POST", body: JSON.stringify(body) });
      localStorage.setItem("token", result.token);
      router.push("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in");
    }
  }

  return (
    <Card className="border-2 border-phonwa-ink/15 bg-white shadow-[3px_3px_0_rgba(42,34,24,0.08)]">
      <div className="mb-4 flex gap-2 text-sm">
        <button
          className={mode === "register" ? "font-semibold text-phonwa-indigo" : "text-phonwa-ink/50"}
          onClick={() => setMode("register")}
          type="button"
        >
          Create a business
        </button>
        <span className="text-phonwa-ink/30">/</span>
        <button
          className={mode === "login" ? "font-semibold text-phonwa-indigo" : "text-phonwa-ink/50"}
          onClick={() => setMode("login")}
          type="button"
        >
          Sign in
        </button>
      </div>
      <form className="space-y-3" onSubmit={submit}>
        {mode === "register" && (
          <div>
            <Label>Business name</Label>
            <Input value={organisationName} onChange={(e) => setOrganisationName(e.target.value)} required />
          </div>
        )}
        <div>
          <Label>Email</Label>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <Label>Password</Label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </div>
        {error && <p className="text-sm text-red-700">{error}</p>}
        <Button className="w-full bg-phonwa-indigo hover:bg-phonwa-indigo/90" type="submit">
          {mode === "login" ? "Sign in" : "Create account"}
        </Button>
      </form>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-phonwa-cream px-6 py-10 text-phonwa-ink">
      <div className="mx-auto flex max-w-md flex-col gap-8">
        <div className="flex items-center justify-between">
          <Link href="/" className="font-display text-2xl text-phonwa-indigo">
            Phonwa
          </Link>
          <Link href="/" className="text-sm text-phonwa-ink/60 hover:text-phonwa-indigo">
            ← Back to home
          </Link>
        </div>
        <Suspense fallback={<div className="rounded-xl border border-line bg-white p-5 text-sm">Loading…</div>}>
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
