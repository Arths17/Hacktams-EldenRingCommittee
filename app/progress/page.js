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
  const [weeklyData, setWeeklyData] = useState([]);
  const [loadingData, setLoadingData] = useState(true);

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
    const token = localStorage.getItem("token") || sessionStorage.getItem("token");
    if (!token) { 
      router.push("/login"); 
      return; 
    }
    
    // Fetch user profile
    fetch(`${API_BASE_URL}/api/me`, {
      headers: { "Authorization": `Bearer ${token}`, "ngrok-skip-browser-warning": "true" },
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

    // Fetch weekly meals data
    if (token) {
      fetchWeeklyMeals(token);
    }
  }, [router]);

  const fetchWeeklyMeals = async (token) => {
    try {
      // Fetch meals for the past 7 days
      const today = new Date();
      const mealsPromises = [];
      const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
      
      for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        const dateStr = date.toISOString().split('T')[0];
        mealsPromises.push(
          fetch(`${API_BASE_URL}/api/meals?date=${dateStr}`, {
            headers: {
              "Authorization": `Bearer ${token}`,
              "ngrok-skip-browser-warning": "true"
            }
          }).then(r => r.json())
        );
      }

      const results = await Promise.all(mealsPromises);
      const weeklyDataCalculated = results.map((result, index) => {
        const date = new Date(today);
        date.setDate(date.getDate() - (6 - index));
        const dayName = dayNames[date.getDay()];
        
        const meals = result.success ? result.meals : [];
        const totals = meals.reduce((acc, meal) => ({
          calories: acc.calories + (meal.total?.calories || 0),
          protein: acc.protein + (meal.total?.protein || 0),
          workouts: acc.workouts // Keep workouts at 0 for now
        }), { calories: 0, protein: 0, workouts: 0 });

        return {
          day: dayName,
          ...totals
        };
      });

      setWeeklyData(weeklyDataCalculated);
    } catch (error) {
      console.error("Failed to fetch weekly meals:", error);
      setWeeklyData([]);
    } finally {
      setLoadingData(false);
    }
  };

  const maxCalories = weeklyData.length > 0 ? Math.max(...weeklyData.map(d => d.calories)) : 0;
  const maxProtein = weeklyData.length > 0 ? Math.max(...weeklyData.map(d => d.protein)) : 0;
  const avgCalories = weeklyData.length > 0 ? Math.round(weeklyData.reduce((sum, d) => sum + d.calories, 0) / weeklyData.length) : 0;
  const avgProtein = weeklyData.length > 0 ? Math.round(weeklyData.reduce((sum, d) => sum + d.protein, 0) / weeklyData.length) : 0;
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
                {loadingData ? (
                  <div className={styles.chartNote}>Loading weekly data...</div>
                ) : weeklyData.length === 0 ? (
                  <div className={styles.chartNote}>No meal data available yet. Start logging meals!</div>
                ) : (
                  weeklyData.map((data, idx) => (
                    <div key={idx} className={styles.barGroup}>
                      <div className={styles.barContainer}>
                        <div 
                          className={styles.bar}
                          style={{ height: `${maxCalories > 0 ? (data.calories / maxCalories) * 100 : 0}%` }}
                          title={`${data.calories} kcal`}
                        />
                      </div>
                      <span className={styles.barLabel}>{data.day}</span>
                    </div>
                  ))
                )}
              </div>
              <p className={styles.chartNote}>Goal: 2400 kcal/day</p>
            </div>

            <div className={styles.chartCard}>
              <h2 className={styles.chartTitle}>💪 Protein Intake</h2>
              <div className={styles.chart}>
                {loadingData ? (
                  <div className={styles.chartNote}>Loading weekly data...</div>
                ) : weeklyData.length === 0 ? (
                  <div className={styles.chartNote}>No meal data available yet. Start logging meals!</div>
                ) : (
                  weeklyData.map((data, idx) => (
                    <div key={idx} className={styles.barGroup}>
                      <div className={styles.barContainer}>
                        <div 
                          className={`${styles.bar} ${styles.barProtein}`}
                          style={{ height: `${maxProtein > 0 ? (data.protein / maxProtein) * 100 : 0}%` }}
                          title={`${data.protein}g`}
                        />
                      </div>
                      <span className={styles.barLabel}>{data.day}</span>
                    </div>
                  ))
                )}
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
