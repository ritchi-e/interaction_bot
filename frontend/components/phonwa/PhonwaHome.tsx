"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { EvervaultCard } from "./EvervaultCard";
import {
  CountUp,
  MagneticCard,
  Marquee,
  Parallax,
  Reveal,
  ScrollProgress,
  Stagger,
  StaggerItem,
  WordReveal,
  motion,
} from "./PhonwaScrollMotion";
import { PhonwaSmoothScroll } from "./PhonwaSmoothScroll";
import { WaterOrb } from "./WaterOrb";

const steps = [
  {
    index: "01",
    title: "Connect the dots",
    body: "Tell us where your agent needs to work — phone, CRM, calendar, or the tools you already use.",
  },
  {
    index: "02",
    title: "Shape the conversation",
    body: "Define the tone, guardrails, knowledge, and handoffs that make your business yours.",
  },
  {
    index: "03",
    title: "Put it to work",
    body: "Go live with a voice agent that answers, calls, qualifies, schedules, and follows through.",
  },
  {
    index: "04",
    title: "Learn from every call",
    body: "See outcomes, listen to patterns, and make the next version even more useful.",
  },
];

const proofNames = [
  "mokhik",
  "smartstudent.ai",
  "finplex",
  "devcortex",
  "digimitra",
  "healyantra",
  "nirmaan",
  "vyoma",
];

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <span></span>
      <span></span>
      <span></span>
    </span>
  );
}

function MiniWave() {
  return (
    <span className="mini-wave" aria-hidden="true">
      <i></i>
      <i></i>
      <i></i>
      <i></i>
      <i></i>
    </span>
  );
}

export function PhonwaHome() {
  const [activeStep, setActiveStep] = useState(0);
  const [navOpen, setNavOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [toastShow, setToastShow] = useState(false);
  const toastTimer = useRef<number | null>(null);

  function showToast(message: string) {
    setToast(message);
    setToastShow(true);
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToastShow(false), 3200);
  }

  function onContactClick() {
    window.setTimeout(() => showToast("Tell us what you want your first agent to do."), 350);
  }

  useEffect(() => {
    return () => {
      if (toastTimer.current) window.clearTimeout(toastTimer.current);
    };
  }, []);

  return (
    <PhonwaSmoothScroll>
      <div className="phonwa-home">
        <ScrollProgress />
        <div className="site-shell">
          <div className="topline">
            <div className="topline-inner">
              <span className="status-dot"></span>
              <span>Phonwa voice agents are live, 24/7</span>
              <a href="#how-it-works">
                See how it works <span aria-hidden="true">↗</span>
              </a>
            </div>
          </div>

          <header className="site-header" id="top">
            <a className="brand" href="#top" aria-label="Phonwa home">
              <BrandMark />
              <span className="brand-name">phonwa</span>
            </a>
            <nav className={`desktop-nav${navOpen ? " mobile-open" : ""}`} aria-label="Primary navigation">
              <a href="#agents" onClick={() => setNavOpen(false)}>
                Agents
              </a>
              <a href="#how-it-works" onClick={() => setNavOpen(false)}>
                How it works
              </a>
              <a href="#why-phonwa" onClick={() => setNavOpen(false)}>
                Why Phonwa
              </a>
            </nav>
            <div className="header-actions">
              <Link className="text-link header-login" href="/login?mode=login">
                Sign in <span aria-hidden="true">↗</span>
              </Link>
              <a className="button button-dark header-cta" href="#contact" onClick={onContactClick}>
                Book a walkthrough <span aria-hidden="true">↗</span>
              </a>
              <button
                className="menu-toggle"
                type="button"
                aria-label="Open navigation"
                aria-expanded={navOpen}
                onClick={() => setNavOpen((o) => !o)}
              >
                <span></span>
                <span></span>
              </button>
            </div>
          </header>

          <main>
            <section className="hero section-pad" aria-labelledby="hero-title">
              <div className="hero-copy">
                <Reveal dir="blur" delay={0.05} duration={1}>
                  <h1 id="hero-title">
                    <WordReveal text="Conversations that keep your business" delay={0.12} />{" "}
                    <em>
                      <WordReveal text="moving." delay={0.55} stagger={0.08} />
                    </em>
                  </h1>
                </Reveal>
                <Reveal dir="up" delay={0.55} duration={0.9}>
                  <p className="hero-lede">
                    Phonwa gives your business a calm, capable voice for every important call — from the first hello to
                    the next best action.
                  </p>
                </Reveal>
              </div>

              <Reveal dir="scale" delay={0.25} duration={1.1} className="hero-visual hero-orb" amount={0.2}>
                <Parallax speed={0.18} className="hero-orb-parallax">
                  <WaterOrb />
                </Parallax>
                <Reveal dir="up" delay={0.7}>
                  <div className="hero-note hero-note-under-orb">
                    <MiniWave /> Natural conversations. Measurable outcomes.
                  </div>
                </Reveal>
              </Reveal>
            </section>

            <section className="signal-strip section-pad" aria-label="Phonwa highlights">
              <Reveal dir="left" className="strip-intro" delay={0.05}>
                <span className="strip-kicker">
                  One voice.
                  <br />
                  <em>Many moments.</em>
                </span>
              </Reveal>
              <Reveal dir="up" className="metric" delay={0.1}>
                <strong>
                  <CountUp value={24} suffix="/7" />
                </strong>
                <span>always-on coverage</span>
              </Reveal>
              <Reveal dir="up" className="metric" delay={0.18}>
                <strong>&lt;1 sec</strong>
                <span>time to respond</span>
              </Reveal>
              <Reveal dir="up" className="metric" delay={0.26}>
                <strong>
                  <CountUp value={10} suffix="+" />
                </strong>
                <span>languages ready to speak</span>
              </Reveal>
              <Reveal dir="right" className="strip-arrow" aria-hidden="true" delay={0.35}>
                ↘
              </Reveal>
            </section>

            <section className="agents-section section-pad" id="agents" aria-labelledby="agents-title">
              <div className="section-heading split-heading">
                <Reveal dir="left" distance={80}>
                  <div>
                    <div className="eyebrow">
                      <span className="eyebrow-line"></span> The Phonwa difference
                    </div>
                    <h2 id="agents-title">
                      Not a bot.
                      <br />
                      <em>A better front line.</em>
                    </h2>
                  </div>
                </Reveal>
                <Reveal dir="right" delay={0.15} distance={60}>
                  <p>
                    Every Phonwa agent is built around your workflow, your tone, and the moments where a fast,
                    human-feeling response makes all the difference.
                  </p>
                </Reveal>
              </div>

              <Stagger className="agent-grid" stagger={0.14} delay={0.08}>
                <StaggerItem dir="left">
                  <MagneticCard className="agent-card agent-card-dark">
                    <div className="agent-card-label">01 / Understand</div>
                    <div className="agent-card-visual visual-listen">
                      <div className="listen-bars">
                        {Array.from({ length: 11 }).map((_, i) => (
                          <i key={i}></i>
                        ))}
                      </div>
                      <span className="listen-caption">“Go ahead, I’m listening.”</span>
                    </div>
                    <h3>Natural by default</h3>
                    <p>
                      Real turn-taking, useful context, and a voice that knows when to speak — and when to pause.
                    </p>
                  </MagneticCard>
                </StaggerItem>

                <StaggerItem dir="up">
                  <MagneticCard className="agent-card agent-card-lime">
                    <div className="agent-card-label">02 / Act</div>
                    <div className="agent-card-visual visual-route">
                      <div className="route-node node-a">Listen</div>
                      <div className="route-line"></div>
                      <div className="route-node node-b">Think</div>
                      <div className="route-line"></div>
                      <div className="route-node node-c">Act</div>
                    </div>
                    <h3>Built for outcomes</h3>
                    <p>
                      From qualifying a lead to booking a follow-up, your agent does more than answer. It moves things
                      forward.
                    </p>
                  </MagneticCard>
                </StaggerItem>

                <StaggerItem dir="right">
                  <MagneticCard className="agent-card agent-card-orange">
                    <div className="agent-card-label">03 / Improve</div>
                    <div className="agent-card-visual visual-chart">
                      <div className="chart-grid"></div>
                      <svg viewBox="0 0 260 100" role="img" aria-label="Upward performance chart">
                        <path
                          d="M5 84 C38 76 42 82 66 62 S97 66 122 48 S150 58 174 37 S205 42 255 11"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="4"
                          strokeLinecap="round"
                        />
                        <circle cx="255" cy="11" r="5" fill="currentColor" />
                      </svg>
                      <span>better, every call</span>
                    </div>
                    <h3>Always getting sharper</h3>
                    <p>
                      See what customers ask, where conversations stall, and what to improve next — in one clear view.
                    </p>
                  </MagneticCard>
                </StaggerItem>
              </Stagger>
            </section>

            <section className="how-section section-pad" id="how-it-works" aria-labelledby="how-title">
              <Reveal dir="left" distance={90} className="how-intro">
                <div className="eyebrow">
                  <span className="eyebrow-line"></span> Simple to start
                </div>
                <h2 id="how-title">
                  From brief
                  <br />
                  <em>to brilliant.</em>
                </h2>
                <p>
                  No lengthy implementation. No mystery handoff. Your team stays in control as Phonwa learns the way you
                  work.
                </p>
                <a className="button button-dark" href="#contact" onClick={onContactClick}>
                  See it in action <span aria-hidden="true">↗</span>
                </a>
              </Reveal>

              <Stagger className="steps-list" stagger={0.12} delay={0.1}>
                {steps.map((step, i) => (
                  <StaggerItem key={step.index} dir="right">
                    <motion.div
                      className={`step${activeStep === i ? " active" : ""}`}
                      onMouseEnter={() => setActiveStep(i)}
                      whileHover={{ x: 10 }}
                      transition={{ type: "spring", stiffness: 380, damping: 28 }}
                    >
                      <span className="step-index">{step.index}</span>
                      <div>
                        <h3>{step.title}</h3>
                        <p>{step.body}</p>
                      </div>
                      <span className="step-arrow">↗</span>
                    </motion.div>
                  </StaggerItem>
                ))}
              </Stagger>
            </section>

            <section className="quote-section section-pad" id="why-phonwa" aria-label="Phonwa proof points">
              <Reveal dir="scale" delay={0.05}>
                <div className="quote-mark">“</div>
              </Reveal>
              <Reveal dir="blur" delay={0.12} duration={1}>
                <blockquote>Phonwa gives every caller the feeling that someone capable is already on it.</blockquote>
              </Reveal>
              <Reveal dir="up" delay={0.25}>
                <div className="quote-meta">
                  <span className="avatar-stack">
                    <i>AK</i>
                    <i>JM</i>
                    <i>SP</i>
                  </span>
                  <span>Designed for teams that care about the details.</span>
                </div>
              </Reveal>
              <Reveal dir="up" delay={0.2} className="proof-row">
                <span>TRUSTED BY TEAMS THAT MOVE FAST</span>
                <Marquee className="proof-marquee" duration={32}>
                  {proofNames.map((name) => (
                    <b key={name}>{name}</b>
                  ))}
                </Marquee>
              </Reveal>
            </section>

            <section className="closing-cta section-pad" id="contact" aria-labelledby="closing-title">
              <Parallax speed={0.35} className="cta-glow glow-one" />
              <Parallax speed={-0.25} className="cta-glow glow-two" />
              <Reveal dir="left" distance={70} className="cta-content" delay={0.05}>
                <div className="eyebrow eyebrow-light">
                  <span className="eyebrow-line"></span> Your next conversation starts here
                </div>
                <h2 id="closing-title">
                  Make every call
                  <br />
                  <em>count for more.</em>
                </h2>
                <p>See what a voice agent built around your business can do.</p>
                <a className="button button-lime" href="mailto:hello@phonwa.ai">
                  Talk to the Phonwa team <span aria-hidden="true">↗</span>
                </a>
              </Reveal>
              <Reveal dir="right" delay={0.2} duration={1} className="cta-evervault" distance={80}>
                <EvervaultCard />
              </Reveal>
            </section>
          </main>

          <footer className="site-footer">
            <div className="footer-main">
              <Reveal dir="up" className="footer-brand">
                <a className="brand brand-footer" href="#top">
                  <BrandMark />
                  <span className="brand-name">phonwa</span>
                </a>
                <p>A better voice for the work that matters.</p>
              </Reveal>
              <Reveal dir="up" delay={0.12} className="footer-links">
                <div>
                  <span className="footer-label">Explore</span>
                  <a href="#agents">Agents</a>
                  <a href="#how-it-works">How it works</a>
                  <a href="#why-phonwa">Why Phonwa</a>
                </div>
                <div>
                  <span className="footer-label">Connect</span>
                  <a href="mailto:hello@phonwa.ai">hello@phonwa.ai</a>
                  <a href="#contact" onClick={onContactClick}>
                    Book a walkthrough
                  </a>
                  <a href="/login?mode=login">Sign in ↗</a>
                </div>
                <div>
                  <span className="footer-label">Read</span>
                  <Link href="/privacy">Privacy</Link>
                  <Link href="/terms">Terms</Link>
                  <Link href="/privacy#processing">Security</Link>
                </div>
              </Reveal>
            </div>
            <div className="footer-bottom">
              <span>© {new Date().getFullYear()} Phonwa Technologies</span>
              <span>Made for conversations worth having.</span>
              <a href="#top">Back to top ↑</a>
            </div>
          </footer>
        </div>
        <div className={`toast${toastShow ? " show" : ""}`} role="status" aria-live="polite">
          {toast}
        </div>
      </div>
    </PhonwaSmoothScroll>
  );
}
