"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "../components/Sidebar/Sidebar";
import Header from "../components/Header/Header";
import StatsCard from "../components/StatsCard/StatsCard";
import MealLog from "../components/MealLog/MealLog";
import styles from "./dashboard.module.css";

const stats = [
  { label: "Calories", value: "1,900", unit: "kcal", icon: "🔥", progress: 79, color: "green" },
  { label: "Protein", value: "108", unit: "g", icon: "💪", progress: 86, color: "gold" },
  { label: "Carbs", value: "197", unit: "g", icon: "🌾", progress: 72, color: "green" },
  { label: "Fat", value: "55", unit: "g", icon: "🥑", progress: 61, color: "gold" },
];

const quickTips = [
  { icon: "💧", text: "You're 2 glasses short of your water goal today." },
  { icon: "🥦", text: "Add more greens — only 1 serving of vegetables logged." },
  { icon: "⚡", text: "Great protein intake! Keep it up." },
];

export default function DashboardPage() {
  const router = useRouter();
  const [username, setUsername] = useState(null);
  const [profile, setProfile] = useState({});

  useEffect(() => {
    fetch("http://localhost:8000/api/me", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) {
          router.push("/login");
        } else {
          setUsername(data.username);
          setProfile(data.profile || {});
        }
      })
      .catch(() => router.push("/login"));
  }, []);

  const displayName = profile.name || username || "there";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className={styles.layout}>
      <Sidebar />
      <div className={styles.main}>
        <Header title="Dashboard" username={username || ""} />
        <div className={styles.content}>

          {/* Welcome Banner */}
          <div className={styles.banner}>
            <div className={styles.bannerText}>
              <h2 className={styles.bannerTitle}>{greeting}, {displayName}! 👋</h2>
              <p className={styles.bannerSub}>
                You&apos;ve logged <strong>3 meals</strong> today. You&apos;re on track to meet your daily goals.
              </p>
            </div>
            <div className={styles.bannerCalGoal}>
              <span className={styles.calCircleLabel}>Daily Goal</span>
              <span className={styles.calCircleVal}>2,400 kcal</span>
            </div>
          </div>

          {/* Stats Cards */}
          <div className={styles.statsGrid}>
            {stats.map((s) => (
              <StatsCard key={s.label} {...s} />
            ))}
          </div>

          {/* Lower section */}
          <div className={styles.lower}>
            <div className={styles.mealLogCol}>
              <MealLog />
            </div>

            {/* Tips & Hydration */}
            <div className={styles.sideCol}>
              {/* Hydration */}
              <div className={styles.card}>
                <h3 className={styles.cardTitle}>💧 Hydration</h3>
                <div className={styles.waterGlasses}>
                  {Array.from({ length: 8 }).map((_, i) => (
                    <div key={i} className={`${styles.glass} ${i < 6 ? styles.filled : ""}`}>
                      💧
                    </div>
                  ))}
                </div>
                <p className={styles.waterText}>6 / 8 glasses</p>
              </div>

              {/* Tips */}
              <div className={styles.card}>
                <h3 className={styles.cardTitle}>✨ Insights</h3>
                <div className={styles.tips}>
                  {quickTips.map((tip, i) => (
                    <div key={i} className={styles.tip}>
                      <span className={styles.tipIcon}>{tip.icon}</span>
                      <span className={styles.tipText}>{tip.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Weekly Summary */}
              <div className={styles.card}>
                <h3 className={styles.cardTitle}>📅 This Week</h3>
                <div className={styles.weekRow}>
                  {["M", "T", "W", "T", "F", "S", "S"].map((day, i) => (
                    <div key={i} className={styles.dayCol}>
                      <div
                        className={styles.dayBar}
                        style={{ height: `${[60, 80, 45, 90, 70, 30, 0][i]}%` }}
                      />
                      <span className={styles.dayLabel}>{day}</span>
                    </div>
                  ))}
                </div>
                <p className={styles.weekNote}>Avg. 1,840 kcal/day this week</p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
