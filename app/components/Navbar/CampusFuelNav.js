"use client";
// app/components/Navbar/CampusFuelNav.js
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import styles from "./CampusFuelNav.module.css";
import { useTheme } from "../ThemeProvider";
import { useApp } from "../../context/AppContext";
import { useRef } from "react";

export default function CampusFuelNav() {
  const pathname = usePathname();
  const { theme, toggle } = useTheme();
  const { logout, user } = useApp();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileMenuRef = useRef(null);

  useEffect(() => {
    setMobileOpen(false);
    setProfileOpen(false);
  }, [pathname]);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === "Escape") {
        setProfileOpen(false);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

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

        <button
          className={styles.mobileToggle}
          type="button"
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          onClick={() => setMobileOpen((prev) => !prev)}
        >
          {mobileOpen ? "✕" : "☰"}
        </button>

        {/* Center: main links */}
        <nav className={`${styles.navLinks} ${mobileOpen ? styles.navLinksOpen : ""}`}>
          <Link href="/dashboard" className={linkClass("/dashboard")}>Dashboard</Link>
          <Link href="/ai" className={linkClass("/ai")}>AI Coach</Link>
          <Link href="/survey" className={linkClass("/survey")}>Survey</Link>
          <Link href="/nutrition" className={linkClass("/nutrition")}>Nutrition</Link>
          <Link href="/progress" className={linkClass("/progress")}>Progress</Link>
          <Link href="/meals" className={linkClass("/meals")}>Meals</Link>
        </nav>

        {/* Right: actions */}
        <div className={`${styles.navActions} ${mobileOpen ? styles.navActionsOpen : ""}`}>
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
          {user && (
            <div className={styles.profileMenuWrap} ref={profileMenuRef}>
              <button
                className={styles.profileTrigger}
                type="button"
                aria-haspopup="menu"
                aria-expanded={profileOpen}
                onClick={() => setProfileOpen((prev) => !prev)}
              >
                <span className={styles.profileAvatar}>
                  {(user?.username || "U").slice(0, 1).toUpperCase()}
                </span>
                <span className={styles.profileText}>Profile</span>
              </button>
              {profileOpen && (
                <div className={styles.profileMenu} role="menu">
                  <button className={styles.menuLogoutBtn} onClick={logout} type="button" role="menuitem">
                    Logout
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

