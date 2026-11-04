"use client";

import { cn } from "@/lib/utils";
import { Mic } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type MouseEvent } from "react";

const TESTIMONIALS = [
  "“Phonwa sounds more human than any bot we’ve tried.” — Priya S., Ops Lead",
  "“Our after-hours calls finally get answered — in Hinglish.” — Arjun M., Clinic Manager",
  "“Follow-ups that used to take a day now happen in minutes.” — Neha K., Care Coordinator",
  "“Patients think they’re talking to our front desk.” — Dr. Mehta, Cloudnine partner",
  "“We booked 3x more demos in the first week.” — Rohan V., Sales Head",
  "“The handoff to a human when needed is seamless.” — Ananya R., CX",
  "“Setup took days, not quarters.” — Vikram T., Founder",
  "“Clear intent, calm tone, real outcomes.” — Sana I., Product",
  "“Our reception never sleeps now.” — Kabir L., Multi-clinic Ops",
  "“Finally a voice agent that gets Indian callers.” — Divya P., Growth",
];

function shuffle<T>(arr: T[]): T[] {
  const next = [...arr];
  for (let i = next.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [next[i], next[j]] = [next[j]!, next[i]!];
  }
  return next;
}

function buildTestimonialFill(minChars = 2200) {
  const parts: string[] = [];
  let total = 0;
  while (total < minChars) {
    for (const quote of shuffle(TESTIMONIALS)) {
      parts.push(quote);
      total += quote.length + 3;
      if (total >= minChars) break;
    }
  }
  return parts.join("   ·   ");
}

export function EvervaultCard({ className }: { className?: string }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [hovered, setHovered] = useState(false);
  const [fill, setFill] = useState("");
  const [pos, setPos] = useState({ x: 180, y: 180 });
  const lastShuffle = useRef(0);

  useEffect(() => {
    setFill(buildTestimonialFill());
  }, []);

  const onMove = useCallback((e: MouseEvent<HTMLDivElement>) => {
    const el = wrapRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    setPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    const now = performance.now();
    // Reshuffle occasionally so text feels alive without thrashing every pixel
    if (now - lastShuffle.current > 90) {
      lastShuffle.current = now;
      setFill(buildTestimonialFill());
    }
  }, []);

  const mask = `radial-gradient(200px circle at ${pos.x}px ${pos.y}px, #000 0%, transparent 72%)`;

  return (
    <div
      ref={wrapRef}
      className={cn("phonwa-evervault relative aspect-square w-full max-w-[360px]", className)}
      onMouseMove={onMove}
      onMouseEnter={(e) => {
        setHovered(true);
        onMove(e);
      }}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="phonwa-evervault-disk relative h-full w-full overflow-hidden rounded-full bg-[#0e1317]">
        <div
          className="pointer-events-none absolute inset-0 rounded-full transition-opacity duration-200"
          style={{
            opacity: hovered ? 1 : 0,
            background: "linear-gradient(135deg, #C9B6FF 0%, #7C5CDB 48%, #5B3FA8 100%)",
            WebkitMaskImage: mask,
            maskImage: mask,
          }}
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-0 overflow-hidden rounded-full transition-opacity duration-200"
          style={{
            opacity: hovered ? 1 : 0,
            WebkitMaskImage: mask,
            maskImage: mask,
          }}
          aria-hidden
        >
          <p
            className="absolute inset-0 select-none break-words whitespace-pre-wrap p-5 font-sans text-[11px] font-semibold leading-[1.45] tracking-normal text-white"
            style={{ wordBreak: "normal", overflowWrap: "anywhere" }}
          >
            {fill}
          </p>
        </div>

        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
          <div className="relative flex h-[44%] w-[44%] items-center justify-center rounded-full bg-[#0e1317]/90 shadow-[0_0_0_1px_rgba(244,240,232,0.08)]">
            <Mic className="h-[52%] w-[52%] text-[#C9B6FF]" strokeWidth={1.55} aria-hidden />
          </div>
        </div>
      </div>
    </div>
  );
}
