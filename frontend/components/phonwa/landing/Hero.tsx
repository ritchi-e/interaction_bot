"use client";

import Link from "next/link";
import { FadeUp, HoverLift } from "./motion";
import { VoiceOrb } from "./VoiceOrb";

export function LandingHero() {
  return (
    <section className="relative overflow-hidden px-5 pb-8 pt-12 md:px-8 md:pb-10 md:pt-20">
      <div className="pointer-events-none absolute inset-0 phonwa-grid-fade" aria-hidden />
      <div
        className="pointer-events-none absolute -left-24 top-10 h-72 w-72 rounded-full blur-3xl"
        style={{ background: "rgba(6,182,196,0.18)" }}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-16 top-32 h-80 w-80 rounded-full blur-3xl"
        style={{ background: "rgba(15,118,110,0.12)" }}
        aria-hidden
      />

      <div className="relative mx-auto grid max-w-6xl items-center gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:gap-12">
        <div>
          <FadeUp>
            <p className="font-display text-5xl font-extrabold tracking-tight text-phonwa-ink sm:text-6xl md:text-7xl">
              Phonwa
            </p>
          </FadeUp>
          <FadeUp delay={0.06}>
            <h1 className="mt-5 max-w-xl font-display text-[1.85rem] font-bold leading-[1.12] tracking-tight text-phonwa-ink sm:text-4xl md:text-[2.65rem]">
              Voice AI that actually sounds human.
            </h1>
          </FadeUp>
          <FadeUp delay={0.12}>
            <p className="mt-5 max-w-lg text-base leading-relaxed text-phonwa-mute md:text-lg">
              Automate reception, hospital follow-ups, and sales calls in Hindi, Hinglish, and English—with fluid
              conversations and enterprise-grade reliability.
            </p>
          </FadeUp>
          <FadeUp delay={0.18} className="mt-8 flex flex-wrap items-center gap-3">
            <HoverLift>
              <Link
                href="/login?mode=register"
                className="inline-flex items-center justify-center rounded-full bg-phonwa-cyan-deep px-6 py-3.5 text-sm font-semibold text-white shadow-[0_12px_30px_-12px_rgba(8,145,178,0.7)]"
              >
                Start Free Trial
              </Link>
            </HoverLift>
            <HoverLift>
              <a
                href="#demos"
                className="inline-flex items-center justify-center rounded-full border border-phonwa-line bg-white px-6 py-3.5 text-sm font-semibold text-phonwa-ink shadow-sm transition hover:border-phonwa-cyan/50"
              >
                Listen to Demos
              </a>
            </HoverLift>
          </FadeUp>
          <FadeUp delay={0.26} className="mt-10 flex flex-wrap gap-x-8 gap-y-3 text-sm text-phonwa-mute">
            <span>
              <strong className="font-semibold text-phonwa-ink">&lt;300ms</strong> reply latency
            </span>
            <span>
              <strong className="font-semibold text-phonwa-ink">HIPAA-minded</strong> call flows
            </span>
            <span>
              <strong className="font-semibold text-phonwa-ink">India-ready</strong> accents
            </span>
          </FadeUp>
        </div>

        <FadeUp delay={0.14} className="relative">
          <div className="absolute inset-6 -z-10 rounded-[2rem] bg-gradient-to-br from-white via-phonwa-mist/80 to-cyan-50 shadow-panel" />
          <VoiceOrb />
          <p className="text-center text-xs font-semibold uppercase tracking-[0.2em] text-phonwa-mute">
            Live conversation signal
          </p>
        </FadeUp>
      </div>
    </section>
  );
}
