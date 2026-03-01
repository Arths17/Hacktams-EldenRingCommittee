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
