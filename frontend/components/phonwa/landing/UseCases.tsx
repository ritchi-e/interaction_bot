"use client";

import { ArrowUpRight, CalendarCheck2, Headset, HeartPulse, MessageSquareHeart } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { FadeUp, motion } from "./motion";

const cases: {
  title: string;
  body: string;
  points: string[];
  icon: LucideIcon;
  className: string;
  accent: string;
}[] = [
  {
    title: "Medical Follow-ups",
    body: "Empathetic discharge check-ins with compliance-aware handoffs when symptoms need a human clinician.",
    points: ["Red-flag escalation", "Hinglish bedside tone", "Care-team notes"],
    icon: HeartPulse,
    className: "md:col-span-2 md:row-span-2",
    accent: "from-cyan-50 to-teal-50",
  },
  {
    title: "24/7 Receptionist",
    body: "Answer, route, and book so no inbound call goes cold after hours.",
    points: ["Appointment booking", "Intent routing"],
    icon: Headset,
    className: "md:col-span-2",
    accent: "from-sky-50 to-white",
  },
  {
    title: "B2B Sales",
    body: "Qualify leads, confirm intent, and set meetings on your calendar.",
    points: ["Outbound + inbound"],
    icon: CalendarCheck2,
    className: "md:col-span-1",
    accent: "from-white to-cyan-50/60",
  },
  {
    title: "Customer Feedback",
    body: "Post-purchase surveys with sentiment capture—without form drop-off.",
    points: ["NPS / CSAT voice"],
    icon: MessageSquareHeart,
    className: "md:col-span-1",
    accent: "from-white to-teal-50/50",
  },
];

export function UseCases() {
  return (
    <section id="use-cases" className="scroll-mt-24 bg-white px-5 py-20 md:px-8 md:py-28">
      <div className="mx-auto max-w-6xl">
        <FadeUp className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-phonwa-teal">Use cases</p>
            <h2 className="mt-3 font-display text-3xl font-bold tracking-tight text-phonwa-ink md:text-4xl">
              Built for the calls Indian teams can&apos;t miss
            </h2>
            <p className="mt-4 text-base leading-relaxed text-phonwa-mute">
              Industry-tuned agents for healthcare trust, always-on reception, pipeline velocity, and voice-of-customer.
            </p>
          </div>
          <a
            href="/login?mode=register"
            className="inline-flex items-center gap-1 text-sm font-semibold text-phonwa-teal hover:text-phonwa-navy"
          >
            Explore a pilot <ArrowUpRight className="h-4 w-4" />
          </a>
        </FadeUp>

        <div className="mt-12 grid grid-cols-1 gap-4 md:grid-cols-4 md:grid-rows-2 md:gap-5">
          {cases.map((item, index) => {
            const Icon = item.icon;
            const featured = item.className.includes("row-span-2");
            return (
              <FadeUp key={item.title} delay={0.05 * index} className={item.className}>
                <motion.article
                  className={`group relative flex h-full flex-col overflow-hidden rounded-[1.6rem] border border-phonwa-line bg-gradient-to-br ${item.accent} p-6 shadow-sm transition duration-300 hover:border-phonwa-cyan/45 hover:shadow-soft md:p-7`}
                  whileHover={{ y: -3 }}
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                >
                  <div className="inline-flex rounded-2xl border border-phonwa-line/80 bg-white/80 p-3 text-phonwa-teal shadow-sm">
                    <Icon className="h-5 w-5" strokeWidth={1.75} />
                  </div>
                  <h3
                    className={`mt-5 font-display font-bold tracking-tight text-phonwa-ink ${featured ? "text-2xl md:text-3xl" : "text-xl"}`}
                  >
                    {item.title}
                  </h3>
                  <p className={`mt-3 leading-relaxed text-phonwa-mute ${featured ? "text-base" : "text-sm"}`}>
                    {item.body}
                  </p>
                  <ul className="mt-5 flex flex-wrap gap-2">
                    {item.points.map((point) => (
                      <li
                        key={point}
                        className="rounded-full border border-phonwa-line/90 bg-white/70 px-3 py-1 text-xs font-medium text-phonwa-navy/80"
                      >
                        {point}
                      </li>
                    ))}
                  </ul>
                </motion.article>
              </FadeUp>
            );
          })}
        </div>
      </div>
    </section>
  );
}
