"use client";

import { ReactLenis } from "lenis/react";
import type { ReactNode } from "react";
import "lenis/dist/lenis.css";

/**
 * Homepage smooth scroll via Lenis (lenis.dev).
 * Uses a root instance so sticky nav, anchors, and IntersectionObserver keep working.
 */
export function PhonwaSmoothScroll({ children }: { children: ReactNode }) {
  return (
    <ReactLenis
      root
      options={{
        autoRaf: true,
        anchors: true,
        syncTouch: true,
        smoothWheel: true,
        lerp: 0.085,
        wheelMultiplier: 0.9,
        touchMultiplier: 1.15,
        // Slightly heavier inertia — more “designed” feel without lag
        duration: 1.15,
        easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      }}
    >
      {children}
    </ReactLenis>
  );
}
