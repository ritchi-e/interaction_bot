"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { api, type User } from "@/lib/api";

const LINKS = [
  { href: "/app", label: "Home" },
  { href: "/app/onboarding", label: "Setup" },
  { href: "/app/campaigns", label: "Campaigns" },
  { href: "/app/leads", label: "Leads" },
  { href: "/app/calls", label: "Calls" },
];

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      router.replace("/");
      return;
    }
    api<User>("/api/auth/me/").then(setUser).catch(() => router.replace("/"));
  }, [router]);

  return (
    <div className="min-h-screen">
      <link rel="stylesheet" href="/styles.css" />
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center justify-between gap-4">
            <Link href="/app" className="font-serif text-xl">
              Caller
            </Link>
            <div className="text-sm text-ink/60 sm:hidden">{user?.organisation_name}</div>
          </div>
          <nav className="flex gap-4 overflow-x-auto text-sm">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={pathname === link.href ? "shrink-0 font-semibold text-pine" : "shrink-0 text-ink/70"}
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="hidden text-sm text-ink/60 sm:block">{user?.organisation_name}</div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
