"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Card, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("register");
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
    <main className="mx-auto grid min-h-screen max-w-5xl items-center gap-12 px-6 py-16 md:grid-cols-2">
      <link rel="stylesheet" href="/styles.css" />
      <div>
        <p className="text-sm font-medium uppercase tracking-wide text-pine">WhatsApp replies, then a call</p>
        <h1 className="mt-3 font-serif text-5xl leading-tight">Talk to the people who answered your campaign.</h1>
        <p className="mt-4 text-ink/70">
          Hindi and Indian English. The agent only says what you put in the campaign: the offer, the prices, and the answers.
        </p>
      </div>
      <Card>
        <div className="mb-4 flex gap-2 text-sm">
          <button className={mode === "register" ? "font-semibold text-pine" : ""} onClick={() => setMode("register")} type="button">
            Create a business
          </button>
          <span className="text-ink/30">/</span>
          <button className={mode === "login" ? "font-semibold text-pine" : ""} onClick={() => setMode("login")} type="button">
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
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required />
          </div>
          {error && <p className="text-sm text-red-700">{error}</p>}
          <Button className="w-full" type="submit">
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
