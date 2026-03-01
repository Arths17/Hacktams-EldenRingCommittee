"use client";

import { useState, useEffect } from "react";
import styles from "./MealLog.module.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const mealTypeColors = {
  Breakfast: "#145A32",
  Lunch: "#C99B4C",
  Snack: "#5b8dee",
  Dinner: "#e05a5a",
};

const mealTypeIcons = {
  Breakfast: "🍳",
  Lunch: "🥗",
  Snack: "🍫",
  Dinner: "🍝",
};

export default function MealLog() {
  const [meals, setMeals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTodaysMeals();
  }, []);

  const fetchTodaysMeals = async () => {
    try {
      const token = localStorage.getItem("token") || sessionStorage.getItem("token");
      if (!token) {
        setLoading(false);
        return;
      }

      const today = new Date().toISOString().split('T')[0];
      const response = await fetch(`${API_BASE_URL}/api/meals?date=${today}`, {
        headers: {
          "Authorization": `Bearer ${token}`,
          "ngrok-skip-browser-warning": "true"
        }
      });

      const data = await response.json();
      if (data.success && data.meals) {
        setMeals(data.meals);
      }
    } catch (error) {
      console.error("Failed to fetch meals:", error);
    } finally {
      setLoading(false);
    }
  };

  const getMealName = (meal) => {
    if (meal.items && meal.items.length > 0) {
      if (meal.items.length === 1) {
        return meal.items[0].name;
      }
      return `${meal.items[0].name} +${meal.items.length - 1} more`;
    }
    return meal.type;
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Today&apos;s Meal Log</h2>
        <a href="/meals" className={styles.addBtn}>+ Add Meal</a>
      </div>
      <div className={styles.list}>
        {loading ? (
          <div className={styles.loading}>Loading meals...</div>
        ) : meals.length === 0 ? (
          <div className={styles.emptyState}>No meals logged today</div>
        ) : (
          meals.map((meal, index) => (
            <div key={meal.timestamp || index} className={styles.row}>
              <div className={styles.iconCol}>
                <span className={styles.icon}>{mealTypeIcons[meal.type] || "🍽️"}</span>
              </div>
              <div className={styles.info}>
                <span className={styles.mealName}>{getMealName(meal)}</span>
                <span className={styles.meta}>
                  <span
                    className={styles.badge}
                    style={{ background: mealTypeColors[meal.type] + "22", color: mealTypeColors[meal.type] }}
                  >
                    {meal.type}
                  </span>
                  <span className={styles.time}>{meal.time}</span>
                </span>
              </div>
              <div className={styles.macros}>
                <span className={styles.macro}>
                  <span className={styles.macroLabel}>Protein</span>
                  <span className={styles.macroVal}>{meal.total?.protein || 0}g</span>
                </span>
                <span className={styles.macro}>
                  <span className={styles.macroLabel}>Carbs</span>
                  <span className={styles.macroVal}>{meal.total?.carbs || 0}g</span>
                </span>
                <span className={styles.macro}>
                  <span className={styles.macroLabel}>Fat</span>
                  <span className={styles.macroVal}>{meal.total?.fat || 0}g</span>
                </span>
              </div>
              <div className={styles.calories}>
                <span className={styles.calVal}>{meal.total?.calories || 0}</span>
                <span className={styles.calLabel}>kcal</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
