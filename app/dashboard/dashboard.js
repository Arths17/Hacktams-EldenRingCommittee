"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import Header from "../components/Header/Header";
import StatsCard from "../components/StatsCard/StatsCard";
import MealLog from "../components/MealLog/MealLog";
import styles from "./dashboard.module.css";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function parseHeightToCm(h) {
  if (!h) return 175;
  const s = String(h).toLowerCase().trim();
  const cmMatch = s.match(/(\d+\.?\d*)\s*cm/);
  if (cmMatch) return parseFloat(cmMatch[1]);
  const ftInMatch = s.match(/(\d+)['"ft\s]+(\d*)/);
  if (ftInMatch) {
    const ft = parseInt(ftInMatch[1]);
    const ins = parseInt(ftInMatch[2] || 0);
    return Math.round(ft * 30.48 + ins * 2.54);
  }
  const num = parseFloat(s);
  if (!isNaN(num)) return num > 100 ? num : num * 30.48;
  return 175;
}

function parseWeightToKg(w) {
  if (!w) return 70;
  const s = String(w).toLowerCase().trim();
  const kgMatch = s.match(/(\d+\.?\d*)\s*kg/);
  if (kgMatch) return parseFloat(kgMatch[1]);
  const lbsMatch = s.match(/(\d+\.?\d*)\s*lb/);
  if (lbsMatch) return parseFloat(lbsMatch[1]) * 0.453592;
  const num = parseFloat(s);
  if (!isNaN(num)) return num > 130 ? num * 0.453592 : num; // heavy bias: >130 likely lbs
  return 70;
}

function computeNutritionGoals(profile) {
  const age = parseInt(profile.age) || 20;
  const gender = (profile.gender || "").toLowerCase();
  const heightCm = parseHeightToCm(profile.height);
  const weightKg = parseWeightToKg(profile.weight);
  const goal = (profile.goal || "maintenance").toLowerCase();
  const workouts = (profile.workout_times || "").toLowerCase();

  // Mifflin-St Jeor BMR
  const bmrM = 10 * weightKg + 6.25 * heightCm - 5 * age + 5;
  const bmrF = 10 * weightKg + 6.25 * heightCm - 5 * age - 161;
  let bmr;
  if (gender.includes("female") || gender.includes("woman")) {
    bmr = bmrF;
  } else if (gender.includes("male") && !gender.includes("female")) {
    bmr = bmrM;
  } else {
    bmr = (bmrM + bmrF) / 2; // non-binary / unknown
  }

  // Activity multiplier based on workout_times
  let activity = 1.2;
  if (!workouts || workouts === "none") {
    activity = 1.2;
  } else if (/[5-7]|daily|every/.test(workouts)) {
    activity = 1.725;
  } else if (/[3-4]/.test(workouts)) {
    activity = 1.55;
  } else {
    activity = 1.375;
  }
  const tdee = bmr * activity;

  // Calorie goal adjusted for body goal
  let calorieGoal;
  if (goal.includes("fat loss") || goal.includes("weight loss")) {
    calorieGoal = Math.round(tdee * 0.80);
  } else if (goal.includes("muscle") || goal.includes("bulk")) {
    calorieGoal = Math.round(tdee * 1.10);
  } else {
    calorieGoal = Math.round(tdee);
  }

  // Macro targets (protein/carbs in g from kcal, fat from kcal/9)
  let proteinG, carbsG, fatG;
  if (goal.includes("fat loss")) {
    proteinG = Math.round((calorieGoal * 0.40) / 4);
    carbsG   = Math.round((calorieGoal * 0.35) / 4);
    fatG     = Math.round((calorieGoal * 0.25) / 9);
  } else if (goal.includes("muscle") || goal.includes("bulk")) {
    proteinG = Math.round((calorieGoal * 0.30) / 4);
    carbsG   = Math.round((calorieGoal * 0.50) / 4);
    fatG     = Math.round((calorieGoal * 0.20) / 9);
  } else {
    proteinG = Math.round((calorieGoal * 0.25) / 4);
    carbsG   = Math.round((calorieGoal * 0.50) / 4);
    fatG     = Math.round((calorieGoal * 0.25) / 9);
  }

  // Water glasses: base 8, +1 if working out
  const waterGlasses = !workouts || workouts === "none" ? 8 : 9;

  return { calorieGoal, proteinG, carbsG, fatG, waterGlasses };
}

function capitalize(s) {
  if (!s) return "";
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function generateInsights(profile, goals) {
  const tips = [];
  const stress  = parseInt(profile.stress_level) || 5;
  const energy  = parseInt(profile.energy_level) || 5;
  const sleep   = (profile.sleep_quality || "").toLowerCase();
  const mood    = (profile.mood || "").toLowerCase();
  const goal    = (profile.goal || "").toLowerCase();
  const diet    = (profile.diet_type || "").toLowerCase();
  const allergies = (profile.allergies || "").toLowerCase();

  // Stress tips
  if (stress >= 7) {
    tips.push({ icon: "😰", text: `Stress is high (${stress}/10) — try magnesium-rich foods: spinach, pumpkin seeds, dark chocolate.` });
  } else if (stress <= 3) {
    tips.push({ icon: "😌", text: "Stress is low — great time to focus on your nutrition goals." });
  }

  // Energy tips
  if (energy <= 3) {
    tips.push({ icon: "⚡", text: `Energy is low (${energy}/10) — eat complex carbs like oats or sweet potato for sustained energy.` });
  } else if (energy >= 8) {
    tips.push({ icon: "🚀", text: `Energy is high (${energy}/10) — capitalize with a strong workout and hit your ${goals.proteinG}g protein target.` });
  }

  // Sleep tips
  if (sleep === "poor") {
    tips.push({ icon: "🌙", text: "Poor sleep quality — include tryptophan-rich foods (turkey, banana, oats) to support better rest." });
  } else if (sleep === "good") {
    tips.push({ icon: "✨", text: "Sleep is solid — your recovery and muscle synthesis are well-supported." });
  }

  // Mood tips
  if (mood === "low") {
    tips.push({ icon: "💙", text: "Mood is low — omega-3 rich foods (walnuts, flaxseed, chia seeds) support brain health and mood." });
  } else if (mood === "good") {
    tips.push({ icon: "😊", text: "Great mood today! Keep fueling it with balanced meals." });
  }

  // Goal tips
  if (goal.includes("muscle") || goal.includes("bulk")) {
    tips.push({ icon: "💪", text: `Muscle gain goal: aim for ${goals.proteinG}g protein and ${goals.calorieGoal.toLocaleString()} kcal today.` });
  } else if (goal.includes("fat loss")) {
    tips.push({ icon: "🔥", text: `Fat loss goal: target ${goals.calorieGoal.toLocaleString()} kcal with ${goals.proteinG}g protein to preserve muscle.` });
  } else if (goal.includes("general")) {
    tips.push({ icon: "🍎", text: "General health goal: prioritize whole foods, fiber, and balanced macros." });
  }

  // Diet-type tips
  if (diet === "vegan") {
    tips.push({ icon: "🌱", text: "As a vegan, ensure you're getting B12, iron, zinc, and complete proteins (quinoa, tempeh, lentils)." });
  } else if (diet === "vegetarian") {
    tips.push({ icon: "🥦", text: "As a vegetarian, combine legumes + grains for complete protein and watch your B12 and iron." });
  } else if (diet === "halal") {
    tips.push({ icon: "🕌", text: "Halal diet: lean halal meats, legumes, and whole grains are great protein sources." });
  }

  // Allergy tips
  if (allergies && allergies !== "none" && allergies !== "n/a" && allergies.length > 2) {
    tips.push({ icon: "⚠️", text: `Allergy alert: avoid ${allergies.split(",")[0].trim()} — check meal labels carefully.` });
  }

  // Fallback
  if (tips.length === 0) {
    tips.push({ icon: "💧", text: "Stay hydrated — aim for 8+ glasses of water today." });
    tips.push({ icon: "🥦", text: "Add more vegetables to hit your micronutrient targets." });
    tips.push({ icon: "⚡", text: "Keep up the great work with your nutrition goals!" });
  }

  return tips.slice(0, 5);
}

// Today's logged meal totals (from MealLog static data)
const LOGGED = { calories: 1900, protein: 108, carbs: 197, fat: 55 };
const WATER_LOGGED = 6;

// ─── Component ───────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const [username, setUsername] = useState(null);
  const [profile, setProfile] = useState({});
  const [goals, setGoals] = useState({ calorieGoal: 2400, proteinG: 150, carbsG: 300, fatG: 65, waterGlasses: 8 });

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.push("/login"); return; }
    fetch("/api/me", {
      headers: { "Authorization": `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) {
          router.push("/login");
        } else {
          setUsername(data.username);
          const p = data.profile || {};
          setProfile(p);
          if (Object.keys(p).length > 0) {
            setGoals(computeNutritionGoals(p));
          }
        }
      })
      .catch(() => router.push("/login"));
  }, []);

  const displayName = profile.name || username || "there";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  const insights = generateInsights(profile, goals);
  const hasProfile = Object.keys(profile).length > 0;

  const stats = [
    {
      label: "Calories",
      value: LOGGED.calories.toLocaleString(),
      unit: "kcal",
      icon: "🔥",
      progress: Math.min(Math.round((LOGGED.calories / goals.calorieGoal) * 100), 110),
      goalText: `/ ${goals.calorieGoal.toLocaleString()} kcal`,
      color: "green",
    },
    {
      label: "Protein",
      value: LOGGED.protein.toString(),
      unit: "g",
      icon: "💪",
      progress: Math.min(Math.round((LOGGED.protein / goals.proteinG) * 100), 110),
      goalText: `/ ${goals.proteinG}g`,
      color: "gold",
    },
    {
      label: "Carbs",
      value: LOGGED.carbs.toString(),
      unit: "g",
      icon: "🌾",
      progress: Math.min(Math.round((LOGGED.carbs / goals.carbsG) * 100), 110),
      goalText: `/ ${goals.carbsG}g`,
      color: "green",
    },
    {
      label: "Fat",
      value: LOGGED.fat.toString(),
      unit: "g",
      icon: "🥑",
      progress: Math.min(Math.round((LOGGED.fat / goals.fatG) * 100), 110),
      goalText: `/ ${goals.fatG}g`,
      color: "gold",
    },
  ];

  return (
    <div className={styles.layout}>
      <CampusFuelNav />
      <div className={styles.main}>
        <Header title="Dashboard" username={username || ""} />
        <div className={styles.content}>

          {/* Welcome Banner */}
          <div className={styles.banner}>
            <div className={styles.bannerText}>
              <h2 className={styles.bannerTitle}>{greeting}, {displayName}! 👋</h2>
              <p className={styles.bannerSub}>
                {hasProfile && profile.goal
                  ? <>Goal: <strong>{capitalize(profile.goal)}</strong> · Diet: <strong>{capitalize(profile.diet_type || "—")}</strong> · You&apos;ve logged <strong>4 meals</strong> today.</>
                  : <>You&apos;ve logged <strong>4 meals</strong> today. You&apos;re on track to meet your daily goals.</>
                }
              </p>
            </div>
            <div className={styles.bannerCalGoal}>
              <span className={styles.calCircleLabel}>Daily Goal</span>
              <span className={styles.calCircleVal}>{goals.calorieGoal.toLocaleString()} kcal</span>
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

            {/* Side column */}
            <div className={styles.sideCol}>

              {/* Hydration */}
              <div className={styles.card}>
                <h3 className={styles.cardTitle}>💧 Hydration</h3>
                <div className={styles.waterGlasses}>
                  {Array.from({ length: goals.waterGlasses }).map((_, i) => (
                    <div key={i} className={`${styles.glass} ${i < WATER_LOGGED ? styles.filled : ""}`}>
                      💧
                    </div>
                  ))}
                </div>
                <p className={styles.waterText}>{WATER_LOGGED} / {goals.waterGlasses} glasses</p>
              </div>

              {/* AI Insights from survey data */}
              <div className={styles.card}>
                <h3 className={styles.cardTitle}>✨ AI Insights</h3>
                <div className={styles.tips}>
                  {insights.map((tip, i) => (
                    <div key={i} className={styles.tip}>
                      <span className={styles.tipIcon}>{tip.icon}</span>
                      <span className={styles.tipText}>{tip.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Profile summary from survey */}
              {hasProfile && (
                <div className={styles.card}>
                  <h3 className={styles.cardTitle}>📋 Your Stats</h3>
                  <div className={styles.tips}>
                    {profile.height && (
                      <div className={styles.tip}>
                        <span className={styles.tipIcon}>📏</span>
                        <span className={styles.tipText}>Height: {profile.height}</span>
                      </div>
                    )}
                    {profile.weight && (
                      <div className={styles.tip}>
                        <span className={styles.tipIcon}>⚖️</span>
                        <span className={styles.tipText}>Weight: {profile.weight}</span>
                      </div>
                    )}
                    {profile.sleep_quality && (
                      <div className={styles.tip}>
                        <span className={styles.tipIcon}>😴</span>
                        <span className={styles.tipText}>Sleep quality: {capitalize(profile.sleep_quality)}</span>
                      </div>
                    )}
                    {profile.stress_level && (
                      <div className={styles.tip}>
                        <span className={styles.tipIcon}>😰</span>
                        <span className={styles.tipText}>Stress level: {profile.stress_level} / 10</span>
                      </div>
                    )}
                    {profile.energy_level && (
                      <div className={styles.tip}>
                        <span className={styles.tipIcon}>⚡</span>
                        <span className={styles.tipText}>Energy level: {profile.energy_level} / 10</span>
                      </div>
                    )}
                    {profile.mood && (
                      <div className={styles.tip}>
                        <span className={styles.tipIcon}>💭</span>
                        <span className={styles.tipText}>Mood: {capitalize(profile.mood)}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

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
                <p className={styles.weekNote}>Avg. {Math.round(goals.calorieGoal * 0.88).toLocaleString()} kcal/day this week</p>
              </div>

            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
