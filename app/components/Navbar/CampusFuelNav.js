"use client";
// app/components/Navbar/CampusFuelNav.js
import { usePathname } from "next/navigation";
import styles from "./CampusFuelNav.module.css";

export default function CampusFuelNav() {
  const pathname = usePathname();

  function linkClass(href) {
    return pathname === href
      ? `${styles.navLink} ${styles.navLinkActive}`
      : styles.navLink;
  }

  return (
    <header className={styles.navbar}>
      <div className={styles.navbarInner}>
        {/* Left: logo */}
        <a href="/" className={styles.brand}>
          <span className={styles.brandMark}>🌿</span>
          <span className={styles.brandText}>CampusFuel</span>
        </a>

        {/* Center: main links */}
        <nav className={styles.navLinks}>
          <a href="/dashboard" className={linkClass("/dashboard")}>Dashboard</a>
          <a href="/ai" className={linkClass("/ai")}>AI Coach</a>
          <a href="/survey" className={linkClass("/survey")}>Survey</a>
          <a href="/nutrition" className={linkClass("/nutrition")}>Nutrition</a>
          <a href="/progress" className={linkClass("/progress")}>Progress</a>
          <a href="/meals" className={linkClass("/meals")}>Meals</a>
        </nav>

        {/* Right: actions */}
        <div className={styles.navActions}>
          <a href="/ai" className={`${styles.btnAi} ${pathname === "/ai" ? styles.btnAiActive : ""}`}>
            🤖 AI Coach
          </a>
        </div>
      </div>
    </header>
  );
}

