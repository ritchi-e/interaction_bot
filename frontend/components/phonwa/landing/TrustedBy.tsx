"use client";

import { FadeUp } from "./motion";

const brands = [
  "Apollo Clinics",
  "Practo Care",
  "Narayana Health",
  "Razorpay",
  "Zoho",
  "Cloudnine",
  "1mg",
  "Pine Labs",
  "Freshworks",
  "Meesho",
];

export function TrustedBy() {
  const row = [...brands, ...brands];
  return (
    <section className="border-y border-phonwa-line bg-white/70 py-11 md:py-14" aria-label="Trusted by">
      <FadeUp className="mx-auto max-w-6xl px-5 md:px-8">
        <p className="mb-7 text-center text-xs font-semibold uppercase tracking-[0.22em] text-phonwa-mute">
          Trusted by operators across India
        </p>
        <div className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-gradient-to-r from-phonwa-snow to-transparent md:w-24" />
          <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-gradient-to-l from-phonwa-snow to-transparent md:w-24" />
          <div className="phonwa-marquee flex w-max items-center gap-3 md:gap-4">
            {row.map((name, i) => (
              <span
                key={`${name}-${i}`}
                className="inline-flex items-center rounded-full border border-phonwa-line bg-white px-5 py-2.5 font-display text-sm font-bold tracking-tight text-phonwa-navy/70 shadow-sm md:text-base"
              >
                {name}
              </span>
            ))}
          </div>
        </div>
      </FadeUp>
    </section>
  );
}
