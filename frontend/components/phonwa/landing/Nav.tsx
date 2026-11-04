"use client";

import Link from "next/link";
import { HoverLift } from "./motion";

const links = [
  { href: "#use-cases", label: "Use Cases" },
  { href: "#demos", label: "Audio Demos" },
  { href: "#pricing", label: "Pricing" },
  { href: "#about", label: "About" },
];

export function LandingNav() {
  return (
    <header className="sticky top-0 z-50 border-b border-phonwa-line/80 bg-white/75 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5 md:h-[4.25rem] md:px-8">
        <Link href="/" className="font-display text-xl font-extrabold tracking-tight text-phonwa-ink md:text-2xl">
          Phonwa
        </Link>

        <nav className="hidden items-center gap-8 text-sm font-medium text-phonwa-mute md:flex">
          {links.map((link) => (
            <a key={link.href} href={link.href} className="transition-colors hover:text-phonwa-ink">
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <Link
            href="/login?mode=login"
            className="hidden text-sm font-medium text-phonwa-mute transition hover:text-phonwa-ink sm:inline"
          >
            Sign in
          </Link>
          <HoverLift>
            <Link
              href="/login?mode=register"
              className="inline-flex items-center rounded-full bg-phonwa-navy px-4 py-2.5 text-sm font-semibold text-white shadow-soft transition hover:bg-phonwa-teal"
            >
              Book a Demo
            </Link>
          </HoverLift>
        </div>
      </div>
    </header>
  );
}
