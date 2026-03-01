"use client";
// app/components/Navbar/CampusFuelNav.js
import { usePathname } from "next/navigation";
import Link from "next/link";
import styles from "./CampusFuelNav.module.css";
import { useTheme } from "../ThemeProvider";

export default function CampusFuelNav() {
  const pathname = usePathname();
  const { theme, toggle } = useTheme();

  function linkClass(href) {
    return pathname === href
      ? `${styles.navLink} ${styles.navLinkActive}`
      : styles.navLink;
  }

  return (
    <header className={styles.navbar}>
      <div className={styles.navbarInner}>
        {/* Left: logo */}
        <Link href="/" className={styles.brand}>
          <span className={styles.brandMark}>🌿</span>
          <span className={styles.brandText}>CampusFuel</span>
        </Link>

        {/* Center: main links */}
        <nav className={styles.navLinks}>
          <Link href="/dashboard" className={linkClass("/dashboard")}>Dashboard</Link>
          <Link href="/ai" className={linkClass("/ai")}>AI Coach</Link>
          <Link href="/survey" className={linkClass("/survey")}>Survey</Link>
          <Link href="/nutrition" className={linkClass("/nutrition")}>Nutrition</Link>
          <Link href="/progress" className={linkClass("/progress")}>Progress</Link>
          <Link href="/meals" className={linkClass("/meals")}>Meals</Link>
        </nav>

        {/* Right: actions */}
        <div className={styles.navActions}>
          <button
            className={styles.themeToggle}
            onClick={toggle}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            title={theme === "dark" ? "Light mode" : "Dark mode"}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
          <Link href="/ai" className={`${styles.btnAi} ${pathname === "/ai" ? styles.btnAiActive : ""}`}>
            🤖 AI Coach
          </Link>
        </div>
      </div>
    </header>
  );
}

