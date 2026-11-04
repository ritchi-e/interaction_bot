"use client";

import { FadeUp } from "./motion";

const steps = [
  {
    n: "01",
    title: "Connect your numbers",
    body: "Point your business lines or WhatsApp calling trunk at Phonwa. No call-centre rack required.",
  },
  {
    n: "02",
    title: "Pick an industry agent",
    body: "Reception, discharge follow-up, sales outbound, or feedback—tuned scripts in Hindi & Hinglish.",
  },
  {
    n: "03",
    title: "Go live with guardrails",
    body: "Forbidden topics, handoffs, and recordings stay under your control. Humans take over when needed.",
  },
];

export function HowItWorks() {
  return (
    <section className="px-5 py-20 md:px-8 md:py-24">
      <div className="mx-auto max-w-6xl">
        <FadeUp className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-phonwa-teal">How it works</p>
          <h2 className="mt-3 font-display text-3xl font-bold tracking-tight text-phonwa-ink md:text-4xl">
            Live in days, not quarters
          </h2>
        </FadeUp>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {steps.map((step, i) => (
            <FadeUp key={step.n} delay={0.08 * i}>
              <div className="h-full rounded-[1.5rem] border border-phonwa-line bg-white p-7 shadow-sm">
                <p className="font-display text-sm font-bold text-phonwa-cyan-deep">{step.n}</p>
                <h3 className="mt-4 font-display text-xl font-bold text-phonwa-ink">{step.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-phonwa-mute">{step.body}</p>
              </div>
            </FadeUp>
          ))}
        </div>
      </div>
    </section>
  );
}
