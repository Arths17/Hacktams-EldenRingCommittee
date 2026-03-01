"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import styles from "./login.module.css";

const particles = [
  { emoji: "🥗", left: "10%",  dur: "14s", delay: "0s",    size: "1.5rem" },
  { emoji: "🍎", left: "25%", dur: "18s", delay: "3.2s",  size: "1.1rem" },
  { emoji: "💪", left: "45%", dur: "11s", delay: "6.5s",  size: "1.4rem" },
  { emoji: "💧", left: "65%", dur: "15s", delay: "1.8s",  size: "1.0rem" },
  { emoji: "🥦", left: "80%", dur: "13s", delay: "9.0s",  size: "1.25rem" },
];

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState(null); // { text, type: "success" | "error" }
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setMessage(null);
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("username", username);
      formData.append("password", password);

      const response = await fetch("/api/login", {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        localStorage.setItem("token", data.token);
        // Clear old profile cache to prevent account mix-ups
        localStorage.removeItem("campusfuel_profile");
        setMessage({ text: "✓ Login successful! Redirecting...", type: "success" });
        setTimeout(() => router.push("/dashboard"), 1000);
      } else {
        setMessage({ text: "✗ Invalid username or password. Please try again.", type: "error" });
      }
    } catch {
      setMessage({ text: "✗ Could not reach the server. Please try again.", type: "error" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.page}>
      {/* Ambient orbs */}
      <div className={`${styles.orb} ${styles.orbGreen}`} />
      <div className={`${styles.orb} ${styles.orbGold}`} />
      
      {/* Floating particles */}
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

      <div className={styles.card}>
        {/* Logo */}
        <div className={styles.brand}>
          <span className={styles.brandIcon}>🌿</span>
          <span className={styles.brandName}>CampusFuel</span>
        </div>

        <h1 className={styles.title}>Welcome back</h1>
        <p className={styles.subtitle}>Sign in to your account</p>

        {message && (
          <div className={`${styles.message} ${styles[message.type]}`}>
            {message.text}
          </div>
        )}

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.field}>
            <label htmlFor="username" className={styles.label}>Username</label>
            <input
              id="username"
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className={styles.input}
              required
              autoComplete="username"
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="password" className={styles.label}>Password</label>
            <input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={styles.input}
              required
              autoComplete="current-password"
            />
          </div>

          <button type="submit" className={styles.btn} disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className={styles.footer}>
          Don&apos;t have an account?{" "}
          <Link href="/signup" className={styles.link}>Sign up</Link>
        </p>
      </div>
    </div>
  );
}
