"use client";

import {
  motion,
  useInView,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
  type HTMLMotionProps,
  type Transition,
} from "framer-motion";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

const ease = [0.22, 1, 0.36, 1] as const;

export type RevealDir = "up" | "down" | "left" | "right" | "scale" | "blur";

const OFFSET: Record<RevealDir, Record<string, number | string>> = {
  up: { y: 56, opacity: 0 },
  down: { y: -40, opacity: 0 },
  left: { x: -72, opacity: 0 },
  right: { x: 72, opacity: 0 },
  scale: { scale: 0.88, opacity: 0 },
  blur: { y: 28, opacity: 0, filter: "blur(12px)" },
};

type RevealProps = {
  children: ReactNode;
  dir?: RevealDir;
  delay?: number;
  duration?: number;
  distance?: number;
  className?: string;
  once?: boolean;
  amount?: number | "some" | "all";
  margin?: string;
} & Omit<HTMLMotionProps<"div">, "children" | "transition">;

export function Reveal({
  children,
  dir = "up",
  delay = 0,
  duration = 0.85,
  distance,
  className,
  once = true,
  amount = 0.22,
  margin = "-10% 0px -8% 0px",
  ...rest
}: RevealProps) {
  const reduce = useReducedMotion();
  const base = { ...OFFSET[dir] };
  if (distance != null) {
    if (dir === "up") base.y = distance;
    if (dir === "down") base.y = -distance;
    if (dir === "left") base.x = -distance;
    if (dir === "right") base.x = distance;
  }

  const transition: Transition = {
    duration: reduce ? 0 : duration,
    delay: reduce ? 0 : delay,
    ease,
  };

  return (
    <motion.div
      className={className}
      initial={reduce ? false : base}
      whileInView={
        reduce
          ? undefined
          : {
              x: 0,
              y: 0,
              scale: 1,
              opacity: 1,
              filter: "blur(0px)",
            }
      }
      viewport={{ once, amount, margin }}
      transition={transition}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

export function Stagger({
  children,
  className,
  stagger = 0.1,
  delay = 0,
  ...rest
}: {
  children: ReactNode;
  className?: string;
  stagger?: number;
  delay?: number;
} & Omit<HTMLMotionProps<"div">, "children">) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : "hidden"}
      whileInView={reduce ? undefined : "show"}
      viewport={{ once: true, amount: 0.18, margin: "-8% 0px" }}
      variants={{
        hidden: {},
        show: {
          transition: {
            staggerChildren: reduce ? 0 : stagger,
            delayChildren: reduce ? 0 : delay,
          },
        },
      }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className,
  dir = "up",
  ...rest
}: {
  children: ReactNode;
  className?: string;
  dir?: RevealDir;
} & Omit<HTMLMotionProps<"div">, "children">) {
  return (
    <motion.div
      className={className}
      variants={{
        hidden: { ...OFFSET[dir] },
        show: {
          x: 0,
          y: 0,
          scale: 1,
          opacity: 1,
          filter: "blur(0px)",
          transition: { duration: 0.8, ease },
        },
      }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/** Split children text into staggered word reveals. */
export function WordReveal({
  text,
  className,
  delay = 0,
  stagger = 0.045,
}: {
  text: string;
  className?: string;
  delay?: number;
  stagger?: number;
}) {
  const reduce = useReducedMotion();
  const words = useMemo(() => text.split(" "), [text]);

  return (
    <motion.span
      className={className}
      initial={reduce ? false : "hidden"}
      whileInView={reduce ? undefined : "show"}
      viewport={{ once: true, amount: 0.4 }}
      variants={{
        hidden: {},
        show: {
          transition: {
            staggerChildren: reduce ? 0 : stagger,
            delayChildren: reduce ? 0 : delay,
          },
        },
      }}
      aria-label={text}
    >
      {words.map((word, i) => (
        <span key={`${word}-${i}`} className="word-mask" aria-hidden="true">
          <motion.span
            className="word-inner"
            variants={{
              hidden: { y: "110%", opacity: 0, rotate: 4 },
              show: {
                y: "0%",
                opacity: 1,
                rotate: 0,
                transition: { duration: 0.75, ease },
              },
            }}
          >
            {word}
            {i < words.length - 1 ? "\u00A0" : ""}
          </motion.span>
        </span>
      ))}
    </motion.span>
  );
}

export function Parallax({
  children,
  className,
  speed = 0.2,
}: {
  children?: ReactNode;
  className?: string;
  speed?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });
  const yRaw = useTransform(scrollYProgress, [0, 1], [speed * 80, speed * -80]);
  const y = useSpring(yRaw, { stiffness: 120, damping: 28, mass: 0.4 });

  return (
    <motion.div ref={ref} className={className} style={reduce ? undefined : { y }}>
      {children}
    </motion.div>
  );
}

export function CountUp({
  value,
  suffix = "",
  prefix = "",
  className,
}: {
  value: number;
  suffix?: string;
  prefix?: string;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.6 });
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(reduce ? value : 0);

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setDisplay(value);
      return;
    }
    const start = performance.now();
    const dur = 1100;
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(value * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, value, reduce]);

  return (
    <span ref={ref} className={className}>
      {prefix}
      {display}
      {suffix}
    </span>
  );
}

export function Marquee({
  children,
  className,
  duration = 28,
}: {
  children: ReactNode;
  className?: string;
  duration?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <div className={`phonwa-marquee${className ? ` ${className}` : ""}`}>
      <motion.div
        className="phonwa-marquee-track"
        animate={reduce ? undefined : { x: ["0%", "-50%"] }}
        transition={
          reduce
            ? undefined
            : { duration, ease: "linear", repeat: Infinity, repeatType: "loop" }
        }
      >
        <div className="phonwa-marquee-group">{children}</div>
        <div className="phonwa-marquee-group" aria-hidden="true">
          {children}
        </div>
      </motion.div>
    </div>
  );
}

export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 140, damping: 28, mass: 0.35 });
  const reduce = useReducedMotion();
  if (reduce) return null;
  return <motion.div className="phonwa-scroll-progress" style={{ scaleX }} />;
}

export function MagneticCard({
  children,
  className,
  ...rest
}: {
  children: ReactNode;
  className?: string;
} & Omit<HTMLMotionProps<"article">, "children">) {
  const reduce = useReducedMotion();
  return (
    <motion.article
      className={className}
      whileHover={
        reduce
          ? undefined
          : {
              y: -10,
              rotateX: 2.5,
              rotateY: -2.5,
              transition: { type: "spring", stiffness: 320, damping: 22 },
            }
      }
      style={{ transformPerspective: 900 }}
      {...rest}
    >
      {children}
    </motion.article>
  );
}

export { motion, ease };
