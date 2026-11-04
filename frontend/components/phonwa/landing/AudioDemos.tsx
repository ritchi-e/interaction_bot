"use client";

import { Pause, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { FadeUp, motion } from "./motion";

type DemoId = "hospital" | "receptionist" | "sales";

const demos: { id: DemoId; label: string; title: string; blurb: string; src: string; meta: string }[] = [
  {
    id: "hospital",
    label: "Hospital Follow-up",
    title: "Discharge check-in with Aditi",
    blurb: "Warm recovery questions, red-flag escalation, and clinician handoff—without sounding scripted.",
    src: "/demos/hospital-followup.wav",
    meta: "Hinglish · Female · Empathy-first",
  },
  {
    id: "receptionist",
    label: "Inbound Receptionist",
    title: "Front desk that never sleeps",
    blurb: "Greets callers, captures intent, and books appointments so no lead waits on hold music.",
    src: "/demos/receptionist.wav",
    meta: "Hindi / Hinglish · Always-on",
  },
  {
    id: "sales",
    label: "Sales Outbound",
    title: "Qualify & set the meeting",
    blurb: "Natural outbound cadence for lead qualification—short turns, clear next steps.",
    src: "/demos/sales-outbound.wav",
    meta: "Hinglish · Outbound",
  },
];

function WaveBars({ active }: { active: boolean }) {
  return (
    <div className="flex h-11 flex-1 items-end gap-[3px]" aria-hidden>
      {Array.from({ length: 48 }).map((_, i) => {
        const base = 7 + ((i * 19) % 24);
        return (
          <motion.span
            key={i}
            className="w-[3px] rounded-full bg-gradient-to-t from-phonwa-teal to-phonwa-cyan"
            animate={
              active
                ? { height: [`${base}px`, `${base + 16}px`, `${base}px`] }
                : { height: `${Math.max(5, base * 0.4)}px` }
            }
            transition={
              active
                ? { duration: 0.7 + (i % 5) * 0.05, repeat: Infinity, ease: "easeInOut", delay: (i % 8) * 0.035 }
                : { duration: 0.25 }
            }
          />
        );
      })}
    </div>
  );
}

export function AudioDemos() {
  const [active, setActive] = useState<DemoId>("hospital");
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const demo = demos.find((d) => d.id === active)!;

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
    audio.currentTime = 0;
    setPlaying(false);
  }, [active]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onEnded = () => setPlaying(false);
    audio.addEventListener("ended", onEnded);
    return () => audio.removeEventListener("ended", onEnded);
  }, []);

  async function togglePlay() {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      setPlaying(false);
      return;
    }
    try {
      await audio.play();
      setPlaying(true);
    } catch {
      setPlaying(false);
    }
  }

  return (
    <section id="demos" className="scroll-mt-24 px-5 py-20 md:px-8 md:py-28">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
          <FadeUp>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-phonwa-teal">Audio demos</p>
            <h2 className="mt-3 font-display text-3xl font-bold tracking-tight text-phonwa-ink md:text-4xl">
              Hear the difference before you buy
            </h2>
            <p className="mt-4 max-w-md text-base leading-relaxed text-phonwa-mute">
              Same voices that run on live PSTN calls. Switch industry tabs and press play.
            </p>
          </FadeUp>
          <FadeUp delay={0.08} className="flex flex-wrap gap-2 lg:justify-end">
            {demos.map((item) => {
              const selected = item.id === active;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActive(item.id)}
                  className={`rounded-full px-4 py-2.5 text-sm font-semibold transition ${
                    selected
                      ? "bg-phonwa-navy text-white shadow-soft"
                      : "border border-phonwa-line bg-white text-phonwa-mute hover:border-phonwa-cyan/40 hover:text-phonwa-ink"
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </FadeUp>
        </div>

        <FadeUp delay={0.14} className="mt-10">
          <div className="overflow-hidden rounded-[1.75rem] border border-phonwa-line bg-white shadow-panel">
            <div className="grid md:grid-cols-[1fr_1.15fr]">
              <div className="border-b border-phonwa-line bg-gradient-to-br from-phonwa-mist/80 to-white p-7 md:border-b-0 md:border-r md:p-9">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-phonwa-teal">{demo.meta}</p>
                <h3 className="mt-3 font-display text-2xl font-bold text-phonwa-ink">{demo.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-phonwa-mute md:text-[0.95rem]">{demo.blurb}</p>
              </div>
              <div className="flex flex-col justify-center p-7 md:p-9">
                <div className="flex items-center gap-4">
                  <button
                    type="button"
                    onClick={togglePlay}
                    aria-label={playing ? "Pause demo" : "Play demo"}
                    className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-phonwa-cyan-deep text-white shadow-[0_14px_30px_-12px_rgba(8,145,178,0.75)] transition hover:scale-105"
                  >
                    {playing ? (
                      <Pause className="h-5 w-5 fill-current" />
                    ) : (
                      <Play className="ml-0.5 h-5 w-5 fill-current" />
                    )}
                  </button>
                  <WaveBars active={playing} />
                </div>
                <p className="mt-5 text-xs text-phonwa-mute">Sample synthesis for evaluation—not a live patient call.</p>
              </div>
            </div>
            <audio ref={audioRef} src={demo.src} preload="metadata" className="hidden" />
          </div>
        </FadeUp>
      </div>
    </section>
  );
}
