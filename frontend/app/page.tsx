import Link from "next/link";
import type { ReactNode } from "react";
import { MarketplaceScene, PhonwaLogoMark, RobotAssistant } from "@/components/phonwa/illustrations";

const features = [
  {
    title: "Reception that never sleeps",
    body: "Answer every missed call in Hindi, Hinglish, or local accents—while you run the shop.",
    doodle: "☎",
  },
  {
    title: "Feels like your neighbourhood",
    body: "Warm greetings, polite follow-ups, and the same chai-stall energy your customers already trust.",
    doodle: "♪",
  },
  {
    title: "Built for Bharat businesses",
    body: "Kiranas, clinics, coaching centres, and service shops—set up in minutes, no call centre needed.",
    doodle: "✦",
  },
];

function SketchButton({
  href,
  children,
  variant = "primary",
}: {
  href: string;
  children: ReactNode;
  variant?: "primary" | "ghost" | "outline";
}) {
  const base =
    "inline-flex items-center justify-center gap-2 px-5 py-3 text-base font-bold transition duration-200 hover:scale-[1.03] active:scale-[0.99]";
  const styles =
    variant === "primary"
      ? "bg-phonwa-indigo text-white sketch-border-sm shadow-doodle hover:shadow-doodle-lg"
      : variant === "outline"
        ? "bg-transparent text-phonwa-ink sketch-border-sm shadow-doodle hover:bg-phonwa-chalk"
        : "bg-phonwa-chalk text-phonwa-ink sketch-border-sm shadow-doodle hover:bg-white";
  return (
    <Link href={href} className={`${base} ${styles}`}>
      {children}
    </Link>
  );
}

export default function PhonwaHomePage() {
  return (
    <div className="min-h-screen bg-phonwa-cream font-sans text-phonwa-ink antialiased">
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "radial-gradient(rgba(42,34,24,0.05) 1px, transparent 1px), radial-gradient(rgba(255,153,51,0.06) 1px, transparent 1px)",
          backgroundSize: "18px 18px, 42px 42px",
          backgroundPosition: "0 0, 10px 14px",
        }}
        aria-hidden
      />

      <header className="relative z-20 mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-5 md:px-8">
        <Link href="/" className="flex items-center gap-2">
          <PhonwaLogoMark className="h-10 w-10" />
          <span className="font-display text-3xl leading-none text-phonwa-indigo md:text-4xl">Phonwa</span>
        </Link>

        <nav className="hidden items-center gap-1 text-sm font-semibold md:flex">
          <a href="#features" className="rounded-full px-3 py-1.5 hover:bg-phonwa-marigold/40">
            <span className="highlighter">Features</span>
          </a>
          <a href="#demo" className="rounded-full px-3 py-1.5 hover:bg-phonwa-teal/15">
            Demo
          </a>
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <Link
            href="/login?mode=login"
            className="px-3 py-2 text-sm font-bold text-phonwa-indigo underline decoration-wavy decoration-phonwa-saffron underline-offset-4 hover:scale-[1.03]"
          >
            Login
          </Link>
          <SketchButton href="/login?mode=login" variant="outline">
            Contact Us
          </SketchButton>
        </div>
      </header>

      <main className="relative z-10">
        <section className="mx-auto grid max-w-6xl items-center gap-8 px-5 pb-10 pt-4 md:grid-cols-[1.05fr_0.95fr] md:gap-6 md:px-8 md:pb-16 md:pt-8">
          <div className="order-1">
            <p className="mb-3 inline-flex items-center gap-2 font-display text-sm text-phonwa-terracotta md:text-base">
              <span aria-hidden>✧</span> Phonwa · AI voice for Bharat
            </p>
            <h1 className="font-hindi text-[2.15rem] font-bold leading-[1.2] text-phonwa-ink sm:text-5xl md:text-[3.35rem]">
              <span className="scribble-underline text-phonwa-saffron">अब AI करेगा बात,</span>
              <br />
              <span className="text-phonwa-indigo">ग्राहक रहेंगे खुश!</span>
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-phonwa-ink/75 md:text-lg">
              AI voice calling assistants for your business—built for India. Automated receptionists, support, and
              assistants on call, in local Indian accents.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <SketchButton href="/login?mode=register" variant="primary">
                Start for Free
              </SketchButton>
              <a
                href="#demo"
                className="inline-flex items-center gap-2 px-4 py-3 font-bold text-phonwa-ink transition hover:scale-[1.03]"
              >
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border-2 border-phonwa-ink bg-phonwa-marigold shadow-doodle">
                  ▶
                </span>
                Watch Video
              </a>
            </div>
            <div className="mt-6 flex flex-wrap gap-3 text-xs font-semibold text-phonwa-ink/60 md:text-sm">
              <span className="sketch-border-sm bg-white/70 px-3 py-1.5">★ No call centre needed</span>
              <span className="sketch-border-sm bg-white/70 px-3 py-1.5">♪ Hindi · Hinglish · more</span>
            </div>
          </div>

          <div className="order-2 relative mx-auto w-full max-w-md md:max-w-none">
            <div className="absolute -left-2 top-6 hidden text-phonwa-marigold sm:block" aria-hidden>
              ★
            </div>
            <div className="animate-phonwa-float">
              <RobotAssistant className="h-auto w-full drop-shadow-sm" />
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 md:px-8">
          <div className="overflow-hidden rounded-doodle border-[2.5px] border-phonwa-ink/80 bg-phonwa-chalk/80 shadow-doodle-lg">
            <MarketplaceScene className="h-auto w-full" />
          </div>
          <p className="mt-3 text-center font-display text-sm text-phonwa-ink/55 md:text-base">
            From kirana counters to clinic desks — Phonwa picks up when you can’t.
          </p>
        </section>

        <section className="mx-auto mt-10 max-w-6xl px-5 md:mt-14 md:px-8">
          <div className="flex flex-col items-center justify-between gap-4 rounded-doodle border-2 border-dashed border-phonwa-ink/25 bg-[#FFF8EE] px-5 py-5 md:flex-row md:px-8">
            <div className="flex flex-wrap items-center justify-center gap-3 md:justify-start">
              <span className="sketch-border-sm bg-white px-3 py-2 text-sm font-bold shadow-doodle">
                🤝 Trust & Security
              </span>
              <span className="sketch-border-sm bg-white px-3 py-2 text-sm font-bold shadow-doodle">
                ✅ 100% Native Accent Guarantee
              </span>
            </div>
            <p className="text-center font-display text-base text-phonwa-indigo md:text-left md:text-lg">
              Built for small businesses, Kiranas, and Clinics{" "}
              <span className="whitespace-nowrap">
                <span aria-hidden>🏪</span> <span aria-hidden>🩺</span> <span aria-hidden>📱</span>
              </span>
            </p>
          </div>
        </section>

        <section id="features" className="mx-auto mt-16 max-w-6xl scroll-mt-24 px-5 md:px-8">
          <div className="mb-8 max-w-2xl">
            <p className="font-display text-phonwa-saffron">Features</p>
            <h2 className="mt-1 font-display text-3xl text-phonwa-indigo md:text-4xl">
              Everyday Indian warmth. Serious AI muscle.
            </h2>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {features.map((feature) => (
              <article
                key={feature.title}
                className="rounded-doodle-sm border-2 border-phonwa-ink/80 bg-white p-5 shadow-doodle transition hover:-translate-y-1 hover:shadow-doodle-lg"
              >
                <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-full border-2 border-phonwa-ink bg-phonwa-marigold font-display text-xl">
                  {feature.doodle}
                </div>
                <h3 className="font-display text-xl text-phonwa-ink">{feature.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-phonwa-ink/70">{feature.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="demo" className="mx-auto mt-16 max-w-6xl scroll-mt-24 px-5 pb-20 md:px-8">
          <div className="rounded-doodle border-[2.5px] border-phonwa-ink bg-gradient-to-br from-phonwa-chalk via-white to-phonwa-teal/10 px-6 py-10 text-center shadow-doodle-lg md:px-12">
            <p className="font-display text-phonwa-terracotta">Demo</p>
            <h2 className="mt-2 font-hindi text-3xl font-bold text-phonwa-indigo md:text-4xl">
              एक कॉल में फर्क महसूस करें
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-phonwa-ink/70">
              Watch how Phonwa greets, answers FAQs, and books the next step—like a polite receptionist who never takes
              a chai break.
            </p>
            <div className="mt-8 flex justify-center">
              <SketchButton href="/login?mode=register">Start for Free</SketchButton>
            </div>
          </div>
        </section>
      </main>

      <footer className="relative z-10 border-t-2 border-dashed border-phonwa-ink/20 bg-[#FFF8EE] px-5 py-8 md:px-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 md:flex-row">
          <div className="flex items-center gap-2">
            <PhonwaLogoMark className="h-8 w-8" />
            <span className="font-display text-xl text-phonwa-indigo">Phonwa</span>
          </div>
          <p className="text-center text-sm text-phonwa-ink/60">
            Made with doodles &amp; chai for businesses across India.
          </p>
          <Link href="/login?mode=login" className="font-bold text-phonwa-indigo underline decoration-wavy underline-offset-4">
            Login to dashboard
          </Link>
        </div>
      </footer>
    </div>
  );
}
