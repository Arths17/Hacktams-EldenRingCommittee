"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import Header from "../components/Header/Header";
import styles from "./progress.module.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ProgressPage() {
  const router = useRouter();
  const [username, setUsername] = useState(null);
  const [profile, setProfile] = useState({});
  const [timeRange, setTimeRange] = useState("week"); // week, month, year
  const [churnRisk, setChurnRisk] = useState(null);

  // Mock data for charts - in production, fetch from API
  const weeklyData = [
    { day: "Mon", calories: 2200, protein: 95, workouts: 1 },
    { day: "Tue", calories: 2400, protein: 110, workouts: 0 },
    { day: "Wed", calories: 1950, protein: 88, workouts: 1 },
    { day: "Thu", calories: 2600, protein: 120, workouts: 1 },
    { day: "Fri", calories: 2300, protein: 102, workouts: 0 },
    { day: "Sat", calories: 1800, protein: 75, workouts: 1 },
    { day: "Sun", calories: 2100, protein: 92, workouts: 0 },
  ];

  const achievements = [
    { id: 1, icon: "🔥", title: "7 Day Streak", description: "Logged meals for 7 days in a row", unlocked: true },
    { id: 2, icon: "💪", title: "Protein Goal", description: "Hit protein goal 5 days this week", unlocked: true },
    { id: 3, icon: "🥗", title: "Healthy Week", description: "Maintained calorie deficit", unlocked: true },
    { id: 4, icon: "🏋️", title: "Workout Warrior", description: "Completed 4 workouts this week", unlocked: false },
    { id: 5, icon: "💧", title: "Hydration Hero", description: "Drank 8 glasses of water daily", unlocked: false },
    { id: 6, icon: "🌟", title: "Perfect Month", description: "Logged every day this month", unlocked: false },
  ];

  const milestones = [
    { date: "2026-02-28", title: "Started using CampusFuel", type: "start" },
    { date: "2026-02-25", title: "First 5-pound loss", type: "weight" },
    { date: "2026-02-20", title: "Completed survey", type: "profile" },
    { date: "2026-02-15", title: "First AI chat", type: "ai" },
  ];

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { 
      router.push("/login"); 
      return; 
    }
    
    // Fetch user profile
    fetch(`${API_BASE_URL}/api/me`, {
      headers: { "Authorization": `Bearer ${token}` },
    })
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
  }, [router]);

  const maxCalories = Math.max(...weeklyData.map(d => d.calories));
  const maxProtein = Math.max(...weeklyData.map(d => d.protein));
  const avgCalories = Math.round(weeklyData.reduce((sum, d) => sum + d.calories, 0) / weeklyData.length);
  const avgProtein = Math.round(weeklyData.reduce((sum, d) => sum + d.protein, 0) / weeklyData.length);
  const totalWorkouts = weeklyData.reduce((sum, d) => sum + d.workouts, 0);

  return (
    <div className={styles.layout}>
      <div className={`${styles.orb} ${styles.orbGreen}`} />
      <div className={`${styles.orb} ${styles.orbGold}`} />
      
      <CampusFuelNav />
      <div className={styles.main}>
        <Header title="Progress & Analytics" username={username || ""} />
        <div className={styles.content}>

          {/* Summary Stats */}
          <div className={styles.summaryGrid}>
            <div className={styles.statCard}>
              <span className={styles.statIcon}>📅</span>
              <div className={styles.statInfo}>
                <p className={styles.statLabel}>Current Streak</p>
                <p className={styles.statValue}>7 days</p>
              </div>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statIcon}>🔥</span>
              <div className={styles.statInfo}>
                <p className={styles.statLabel}>Avg. Calories</p>
                <p className={styles.statValue}>{avgCalories} kcal</p>
              </div>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statIcon}>💪</span>
              <div className={styles.statInfo}>
                <p className={styles.statLabel}>Avg. Protein</p>
                <p className={styles.statValue}>{avgProtein}g</p>
              </div>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statIcon}>🏋️</span>
              <div className={styles.statInfo}>
                <p className={styles.statLabel}>Workouts</p>
                <p className={styles.statValue}>{totalWorkouts} this week</p>
              </div>
            </div>
          </div>

          {/* Charts Section */}
          <div className={styles.chartsSection}>
            <div className={styles.chartCard}>
              <div className={styles.chartHeader}>
                <h2 className={styles.chartTitle}>📊 Calorie Trends</h2>
                <div className={styles.timeRangeButtons}>
                  <button 
                    className={`${styles.timeButton} ${timeRange === "week" ? styles.active : ""}`}
                    onClick={() => setTimeRange("week")}
                  >
                    Week
                  </button>
                  <button 
                    className={`${styles.timeButton} ${timeRange === "month" ? styles.active : ""}`}
                    onClick={() => setTimeRange("month")}
                  >
                    Month
                  </button>
                  <button 
                    className={`${styles.timeButton} ${timeRange === "year" ? styles.active : ""}`}
                    onClick={() => setTimeRange("year")}
                  >
                    Year
                  </button>
                </div>
              </div>
              <div className={styles.chart}>
                {weeklyData.map((data, idx) => (
                  <div key={idx} className={styles.barGroup}>
                    <div className={styles.barContainer}>
                      <div 
                        className={styles.bar}
                        style={{ height: `${(data.calories / maxCalories) * 100}%` }}
                        title={`${data.calories} kcal`}
                      />
                    </div>
                    <span className={styles.barLabel}>{data.day}</span>
                  </div>
                ))}
              </div>
              <p className={styles.chartNote}>Goal: 2400 kcal/day</p>
            </div>

            <div className={styles.chartCard}>
              <h2 className={styles.chartTitle}>💪 Protein Intake</h2>
              <div className={styles.chart}>
                {weeklyData.map((data, idx) => (
                  <div key={idx} className={styles.barGroup}>
                    <div className={styles.barContainer}>
                      <div 
                        className={`${styles.bar} ${styles.barProtein}`}
                        style={{ height: `${(data.protein / maxProtein) * 100}%` }}
                        title={`${data.protein}g`}
                      />
                    </div>
                    <span className={styles.barLabel}>{data.day}</span>
                  </div>
                ))}
              </div>
              <p className={styles.chartNote}>Goal: 108g/day</p>
            </div>
          </div>

          {/* Achievements */}
          <div className={styles.achievementsCard}>
            <h2 className={styles.achievementsTitle}>🏆 Achievements</h2>
            <div className={styles.achievementsGrid}>
              {achievements.map((achievement) => (
                <div 
                  key={achievement.id} 
                  className={`${styles.achievement} ${achievement.unlocked ? styles.unlocked : styles.locked}`}
                >
                  <div className={styles.achievementIcon}>{achievement.icon}</div>
                  <div className={styles.achievementInfo}>
                    <h3 className={styles.achievementTitle}>{achievement.title}</h3>
                    <p className={styles.achievementDesc}>{achievement.description}</p>
                  </div>
                  {achievement.unlocked && <span className={styles.unlockedBadge}>✓</span>}
                </div>
              ))}
            </div>
          </div>

          {/* Timeline */}
          <div className={styles.timelineCard}>
            <h2 className={styles.timelineTitle}>📜 Your Journey</h2>
            <div className={styles.timeline}>
              {milestones.map((milestone, idx) => (
                <div key={idx} className={styles.timelineItem}>
                  <div className={styles.timelineDot} />
                  <div className={styles.timelineContent}>
                    <p className={styles.timelineDate}>{milestone.date}</p>
                    <p className={styles.timelineText}>{milestone.title}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Engagement Health */}
          <div className={styles.engagementCard}>
            <h2 className={styles.engagementTitle}>💚 Engagement Health</h2>
            <p className={styles.engagementDesc}>
              You&apos;re doing great! Your consistent logging and engagement show strong commitment.
            </p>
            <div className={styles.engagementMeter}>
              <div className={styles.meterBar}>
                <div className={styles.meterFill} style={{ width: "85%" }} />
              </div>
              <p className={styles.meterLabel}>85% Engagement Score</p>
            </div>
            <div className={styles.engagementTips}>
              <div className={styles.engagementTip}>
                <span className={styles.tipIcon}>✅</span>
                <span className={styles.tipText}>Regular meal logging</span>
              </div>
              <div className={styles.engagementTip}>
                <span className={styles.tipIcon}>✅</span>
                <span className={styles.tipText}>Active AI coach usage</span>
              </div>
              <div className={styles.engagementTip}>
                <span className={styles.tipIcon}>⚠️</span>
                <span className={styles.tipText}>Try adding more workout tracking</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
