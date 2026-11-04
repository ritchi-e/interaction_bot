"use client";

import { motion } from "framer-motion";

/** Soft speech orb tuned for the light landing surface. */
export function VoiceOrb() {
  return (
    <div className="relative mx-auto flex h-[300px] w-full max-w-lg items-center justify-center md:h-[380px]">
      <div
        className="absolute inset-0 rounded-[2.5rem] opacity-90"
        style={{
          background:
            "radial-gradient(circle at 35% 30%, rgba(6,182,196,0.22), transparent 42%), radial-gradient(circle at 75% 65%, rgba(15,118,110,0.14), transparent 45%)",
        }}
        aria-hidden
      />

      {[0, 1, 2, 3].map((i) => (
        <motion.div
          key={i}
          className="absolute rounded-full border border-phonwa-cyan/25"
          style={{ width: 120 + i * 48, height: 120 + i * 48 }}
          animate={{ scale: [1, 1.045, 1], opacity: [0.25, 0.5, 0.25] }}
          transition={{ duration: 3.4 + i * 0.35, repeat: Infinity, ease: "easeInOut", delay: i * 0.2 }}
          aria-hidden
        />
      ))}

      <motion.div
        className="relative z-10 flex h-32 w-32 items-center justify-center rounded-full md:h-40 md:w-40"
        style={{
          background: "linear-gradient(160deg, #67E8F9 0%, #06B6C4 48%, #0F766E 100%)",
          boxShadow: "0 24px 60px -20px rgba(8, 145, 178, 0.55), inset 0 1px 0 rgba(255,255,255,0.55)",
        }}
        animate={{ scale: [1, 1.035, 1] }}
        transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
      >
        <div className="flex h-14 items-end gap-1.5">
          {[5, 11, 17, 9, 20, 8, 15, 6, 12].map((h, idx) => (
            <motion.span
              key={idx}
              className="w-1.5 rounded-full bg-white/90 md:w-2"
              animate={{ height: [`${h * 1.8}px`, `${h * 3}px`, `${h * 1.8}px`] }}
              transition={{
                duration: 0.85 + (idx % 3) * 0.12,
                repeat: Infinity,
                ease: "easeInOut",
                delay: idx * 0.07,
              }}
            />
          ))}
        </div>
      </motion.div>
    </div>
  );
}
