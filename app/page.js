"use client";

import { useEffect } from "react";
import Link from "next/link";
import styles from "./landing.module.css";

const features = [
  {
    icon: "🧠",
    iconClass: "",
    title: "AI-Powered Nutrition Coach",
    desc: "Chat with an intelligent coach trained on your goals, dietary needs, and campus dining options.",
  },
  {
    icon: "📊",
    iconClass: "gold",
    title: "Real-Time Macro Tracking",
    desc: "Log meals and see calories, protein, carbs, and fat update instantly against your daily targets.",
  },
  {
    icon: "🥗",
    iconClass: "",
    title: "Smart Meal Suggestions",
    desc: "Get personalised meal ideas based on your profile, energy levels, and what's available nearby.",
  },
  {
    icon: "💧",
    iconClass: "gold",
    title: "Hydration Reminders",
    desc: "Stay on top of your water intake with gentle nudges throughout the day.",
  },
  {
    icon: "📈",
    iconClass: "",
    title: "Progress Dashboard",
    desc: "Visualise weekly trends and celebrate wins with a clean, at-a-glance dashboard.",
  },
  {
    icon: "🎯",
    iconClass: "gold",
    title: "Goal-Based Profiles",
    desc: "Set targets for weight, performance, or energy and let CampusFuel keep you on track.",
  },
];

const steps = [
  {
    num: "1",
    title: "Create your profile",
    desc: "Answer a quick survey so we understand your goals and lifestyle.",
  },
  {
    num: "2",
    title: "Log your meals",
    desc: "Add food from our nutrition database and track macros with ease.",
  },
  {
    num: "3",
    title: "Chat with your AI coach",
    desc: "Ask anything — meal ideas, nutrition advice, or a motivational boost.",
  },
  {
    num: "4",
    title: "Watch yourself improve",
    desc: "Review trends weekly and adjust your plan as your body evolves.",
  },
];

const particles = [
  { emoji: "🥗", left: "6%",  dur: "14s", delay: "0s",    size: "1.5rem" },
  { emoji: "🍎", left: "16%", dur: "18s", delay: "3.2s",  size: "1.1rem" },
  { emoji: "💪", left: "27%", dur: "11s", delay: "6.5s",  size: "1.4rem" },
  { emoji: "💧", left: "40%", dur: "15s", delay: "1.8s",  size: "1.0rem" },
  { emoji: "🥦", left: "53%", dur: "13s", delay: "9.0s",  size: "1.25rem" },
  { emoji: "🏃", left: "65%", dur: "16s", delay: "4.4s",  size: "1.1rem" },
  { emoji: "🍌", left: "76%", dur: "12s", delay: "7.7s",  size: "1.3rem" },
  { emoji: "⚡", left: "88%", dur: "10s", delay: "2.1s",  size: "1.0rem" },
  { emoji: "🫐", left: "33%", dur: "17s", delay: "11.3s", size: "1.15rem" },
  { emoji: "🥑", left: "58%", dur: "20s", delay: "5.9s",  size: "1.2rem" },
];

const tickerItems = [
  { icon: "🔥", text: "Track every calorie — know exactly what you're fuelling with" },
  { icon: "💪", text: "Protein goal hit? Your muscles will thank you" },
  { icon: "💧", text: "8 glasses a day keeps the brain fog away" },
  { icon: "🧠", text: "AI Coach available 24/7 — ask anything, anytime" },
  { icon: "🥦", text: "Aim for 5 colourful servings of veg every day" },
  { icon: "📊", text: "Weekly insights to keep your progress on track" },
  { icon: "⚡", text: "Energy peaks at 10am — time your biggest meals right" },
  { icon: "🎯", text: "Set a goal, build a streak, become unstoppable" },
  { icon: "🍌", text: "Complex carbs = sustained energy for long study sessions" },
  { icon: "🏃", text: "Active students burn up to 500 extra kcal per day" },
];

export default function LandingPage() {
  useEffect(() => {
    const els = document.querySelectorAll("." + styles.reveal);
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add(styles.visible);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);
  return (
    <div style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
      {/* ── Navbar ── */}
      <nav className={styles.nav}>
        <a href="/" className={styles.brand}>
          <span className={styles.brandIcon}>🌿</span>
          <span className={styles.brandName}>CampusFuel</span>
        </a>
        <div className={styles.navActions}>
          <Link href="/login" className={styles.btnOutline}>
            Log in
          </Link>
          <Link href="/signup" className={styles.btnFill}>
            Sign up free
          </Link>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className={styles.hero}>
        {/* ambient orbs */}
        <div className={`${styles.orb} ${styles.orbGreen}`} />
        <div className={`${styles.orb} ${styles.orbGold}`} />
        {/* floating particles */}
        <div className={styles.particles}>
          {particles.map((p, i) => (
            <span
              key={i}
              className={styles.particle}
              style={{
                left: p.left,
                fontSize: p.size,
                animationDuration: p.dur,
                animationDelay: p.delay,
              }}
            >
              {p.emoji}
            </span>
          ))}
        </div>
        <div className={styles.heroInner}>
          <span className={styles.heroTag}>🌱 Campus Nutrition, Simplified</span>
          <h1 className={styles.heroTitle}>
            Fuel your body,<br />
            <span>ace your day.</span>
          </h1>
          <p className={styles.heroSub}>
            CampusFuel is the AI-powered nutrition companion built for students.
            Track meals, hit your macros, and get personalised advice — all in one place.
          </p>
          <div className={styles.heroCta}>
            <Link href="/signup" className={styles.btnHero}>
              Get started for free →
            </Link>
            <Link href="/ai" className={styles.btnHeroAlt}>
              🤖 Try the AI Coach
            </Link>
          </div>
        </div>
      </section>

      {/* ── Ticker ── */}
      <div className={styles.ticker}>
        <div className={styles.tickerTrack}>
          {[...tickerItems, ...tickerItems].map((t, i) => (
            <span key={i} className={styles.tickerItem}>
              <span className={styles.tickerDot}>{t.icon}</span>
              {t.text}
              {i < tickerItems.length * 2 - 1 && (
                <span className={styles.tickerDot} style={{ marginLeft: "2.5rem", opacity: 0.4 }}>•</span>
              )}
            </span>
          ))}
        </div>
      </div>

      {/* ── Stats Bar ── */}
      <div className={styles.statsBar}>
        <div className={`${styles.stat} ${styles.reveal} ${styles.delay1}`}>
          <div className={styles.statValue}>10k+</div>
          <div className={styles.statLabel}>Students tracked</div>
        </div>
        <div className={`${styles.stat} ${styles.reveal} ${styles.delay2}`}>
          <div className={styles.statValue}>500k+</div>
          <div className={styles.statLabel}>Meals logged</div>
        </div>
        <div className={`${styles.stat} ${styles.reveal} ${styles.delay3}`}>
          <div className={styles.statValue}>95%</div>
          <div className={styles.statLabel}>Hit weekly goals</div>
        </div>
        <div className={`${styles.stat} ${styles.reveal} ${styles.delay4}`}>
          <div className={styles.statValue}>24/7</div>
          <div className={styles.statLabel}>AI Coach available</div>
        </div>
      </div>

      {/* ── Features ── */}
      <section className={styles.features}>
        <div className={`${styles.sectionHead} ${styles.reveal}`}>
          <span className={styles.sectionTag}>Features</span>
          <h2 className={styles.sectionTitle}>Everything you need to eat well on campus</h2>
          <p className={styles.sectionSub}>
            From macro tracking to AI coaching, CampusFuel gives you the tools to build healthy habits that last.
          </p>
        </div>
        <div className={styles.featureGrid}>
          {features.map((f, i) => (
            <div key={f.title} className={`${styles.featureCard} ${styles.reveal} ${[styles.delay1, styles.delay2, styles.delay3, styles.delay4][i % 4]}`}>
              <div className={`${styles.featureIcon} ${f.iconClass === "gold" ? styles.gold : ""}`}>
                {f.icon}
              </div>
              <div className={styles.featureTitle}>{f.title}</div>
              <div className={styles.featureDesc}>{f.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section className={styles.howItWorks}>
        <div className={`${styles.sectionHead} ${styles.reveal}`}>
          <span className={styles.sectionTag}>How it works</span>
          <h2 className={styles.sectionTitle}>Up and running in minutes</h2>
          <p className={styles.sectionSub}>
            No complicated setup. Just sign up, fill in your profile, and start fuelling smarter.
          </p>
        </div>
        <div className={styles.steps}>
          {steps.map((s, i) => (
            <div key={s.num} className={`${styles.step} ${styles.reveal} ${[styles.delay1, styles.delay2, styles.delay3, styles.delay4][i]}`}>
              <div className={styles.stepNum}>{s.num}</div>
              <div className={styles.stepTitle}>{s.title}</div>
              <div className={styles.stepDesc}>{s.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className={styles.ctaBanner}>
        <h2 className={`${styles.ctaTitle} ${styles.reveal}`}>Ready to fuel your best semester?</h2>
        <p className={`${styles.ctaSub} ${styles.reveal} ${styles.delay1}`}>
          Join thousands of students already hitting their nutrition goals with CampusFuel.
        </p>
        <div className={`${styles.reveal} ${styles.delay2}`} style={{ display: "inline-block" }}>
          <Link href="/signup" className={styles.btnCtaWhite}>
            Create your free account →
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className={styles.footer}>
        <div className={styles.footerBrand}>
          <span>🌿</span>
          <span>CampusFuel</span>
        </div>
        <div className={styles.footerCopy}>© 2026 CampusFuel. Built for students, by students.</div>
      </footer>
    </div>
  );
}
