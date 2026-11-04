"use client";

import Link from "next/link";
import { FadeUp, HoverLift } from "./motion";

const columns = [
  {
    title: "Product",
    links: [
      { label: "Use Cases", href: "#use-cases" },
      { label: "Audio Demos", href: "#demos" },
      { label: "Pricing", href: "#pricing" },
      { label: "Book a Demo", href: "/login?mode=register" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "#about" },
      { label: "Sign in", href: "/login?mode=login" },
      { label: "Contact", href: "mailto:hello@phonwa.online" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", href: "/privacy" },
      { label: "Terms of Service", href: "/terms" },
      { label: "Data Processing", href: "/privacy#processing" },
    ],
  },
];

export function LandingFooter() {
  return (
    <footer id="about" className="scroll-mt-24 border-t border-phonwa-line bg-white">
      <div className="mx-auto max-w-6xl px-5 py-16 md:px-8">
        <FadeUp
          id="pricing"
          className="scroll-mt-24 overflow-hidden rounded-[1.75rem] border border-phonwa-line bg-gradient-to-br from-phonwa-navy via-[#0E4A5C] to-phonwa-teal p-8 text-white shadow-soft md:flex md:items-center md:justify-between md:p-10"
        >
          <div className="max-w-xl">
            <h2 className="font-display text-2xl font-bold md:text-3xl">Simple pricing for serious teams</h2>
            <p className="mt-3 text-sm leading-relaxed text-white/75 md:text-base">
              Start with a pilot clinic or sales pod, then scale minutes across India. Custom enterprise plans with DPA
              and SSO.
            </p>
          </div>
          <HoverLift className="mt-6 shrink-0 md:mt-0">
            <Link
              href="/login?mode=register"
              className="inline-flex rounded-full bg-white px-5 py-3 text-sm font-semibold text-phonwa-navy shadow-sm"
            >
              Talk to sales
            </Link>
          </HoverLift>
        </FadeUp>

        <FadeUp className="mt-14 grid gap-10 md:grid-cols-4">
          <div>
            <p className="font-display text-2xl font-extrabold tracking-tight text-phonwa-ink">Phonwa</p>
            <p className="mt-3 max-w-xs text-sm leading-relaxed text-phonwa-mute">
              Enterprise voice agents for reception, patient follow-ups, sales, and feedback—built for Indian businesses.
            </p>
          </div>
          {columns.map((col) => (
            <div key={col.title}>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-phonwa-navy/70">{col.title}</p>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    {link.href.startsWith("mailto:") || link.href.startsWith("/") ? (
                      <Link href={link.href} className="text-sm text-phonwa-mute transition hover:text-phonwa-ink">
                        {link.label}
                      </Link>
                    ) : (
                      <a href={link.href} className="text-sm text-phonwa-mute transition hover:text-phonwa-ink">
                        {link.label}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </FadeUp>

        <div className="mt-10 flex flex-col gap-3 border-t border-phonwa-line pt-6 text-xs text-phonwa-mute sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} Phonwa. All rights reserved.</p>
          <div className="flex gap-4">
            <a href="https://www.linkedin.com" className="hover:text-phonwa-ink" rel="noreferrer" target="_blank">
              LinkedIn
            </a>
            <a href="https://x.com" className="hover:text-phonwa-ink" rel="noreferrer" target="_blank">
              X
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
