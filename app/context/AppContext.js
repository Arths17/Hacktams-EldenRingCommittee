"use client";

import { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const AppContext = createContext();

async function parseApiResponse(response, fallbackMessage) {
  const rawText = await response.text();
  let data = null;

  try {
    data = rawText ? JSON.parse(rawText) : {};
  } catch {
    data = null;
  }

  const explicitError =
    data?.error ||
    data?.detail ||
    data?.message ||
    data?.error_code;

  if (!response.ok || data?.success === false) {
    const fallback = `${fallbackMessage} (${response.status})`;
    const nonJsonHint = !data && rawText ? ` ${rawText.slice(0, 120)}` : "";
    return {
      ok: false,
      error: explicitError || `${fallback}${nonJsonHint}`,
      data: data || {},
    };
  }

  return { ok: true, data: data || {} };
}

function isNotFoundError(errorMessage) {
  if (!errorMessage) return false;
  const msg = String(errorMessage).toLowerCase();
  return msg.includes("not found") || msg.includes("(404)") || msg.includes(" 404");
}

function getLastNDates(n) {
  const dates = [];
  for (let i = n - 1; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    dates.push(date.toISOString().split("T")[0]);
  }
  return dates;
}

function deriveWeeklyMeals(meals) {
  const dates = getLastNDates(7);
  return dates.map((date) => {
    const dayMeals = meals.filter((meal) => meal.date === date);
    const totals = dayMeals.reduce(
      (acc, meal) => ({
        calories: acc.calories + (meal.total?.calories || 0),
        protein: acc.protein + (meal.total?.protein || 0),
        carbs: acc.carbs + (meal.total?.carbs || 0),
        fat: acc.fat + (meal.total?.fat || 0),
      }),
      { calories: 0, protein: 0, carbs: 0, fat: 0 }
    );
    return { date, ...totals };
  });
}

function deriveTodayMeals(meals) {
  const today = new Date().toISOString().split("T")[0];
  return meals.filter((meal) => meal.date === today);
}

function deriveActivityMetrics(meals) {
  const byDate = meals.reduce((acc, meal) => {
    if (!meal?.date) return acc;
    if (!acc[meal.date]) acc[meal.date] = [];
    acc[meal.date].push(meal);
    return acc;
  }, {});

  const datesLogged = Object.keys(byDate).sort();
  const firstLoggedDate = datesLogged[0] || null;
  const totalMeals = meals.length;
  const loggedDays = datesLogged.length;

  let currentStreak = 0;
  const cursor = new Date();
  while (true) {
    const key = cursor.toISOString().split("T")[0];
    if (byDate[key] && byDate[key].length > 0) {
      currentStreak += 1;
      cursor.setDate(cursor.getDate() - 1);
    } else {
      break;
    }
  }

  const weeklyTotals = deriveWeeklyMeals(meals);
  const proteinGoalDays = weeklyTotals.filter((d) => d.protein >= 108).length;
  const calorieGoalDays = weeklyTotals.filter((d) => d.calories >= 1800 && d.calories <= 2400).length;
  const perfectWeek = weeklyTotals.every((d) => d.calories > 0);

  const achievements = [
    {
      id: 1,
      icon: "🔥",
      title: "7 Day Streak",
      description: "Logged meals for 7 days in a row",
      unlocked: currentStreak >= 7,
    },
    {
      id: 2,
      icon: "💪",
      title: "Protein Goal",
      description: "Hit protein goal 3+ days this week",
      unlocked: proteinGoalDays >= 3,
    },
    {
      id: 3,
      icon: "🥗",
      title: "Healthy Week",
      description: "Stayed in calorie range for 4+ days",
      unlocked: calorieGoalDays >= 4,
    },
    {
      id: 4,
      icon: "🏁",
      title: "First Meal Logged",
      description: "Logged your first meal",
      unlocked: totalMeals >= 1,
    },
    {
      id: 5,
      icon: "🗓️",
      title: "Consistent Logger",
      description: "Logged meals on 14 different days",
      unlocked: loggedDays >= 14,
    },
    {
      id: 6,
      icon: "🌟",
      title: "Perfect Week",
      description: "Logged meals every day this week",
      unlocked: perfectWeek,
    },
  ];

  const milestones = [];
  if (firstLoggedDate) {
    milestones.push({ date: firstLoggedDate, title: "Started using CampusFuel", type: "start" });
  }
  if (totalMeals >= 1) {
    const firstMeal = meals
      .slice()
      .sort((a, b) => new Date(a.timestamp || 0) - new Date(b.timestamp || 0))[0];
    if (firstMeal?.date) {
      milestones.push({ date: firstMeal.date, title: "Logged first meal", type: "meal" });
    }
  }
  if (currentStreak >= 7) {
    milestones.push({ date: new Date().toISOString().split("T")[0], title: "Reached 7-day streak", type: "streak" });
  }
  if (proteinGoalDays >= 3) {
    milestones.push({ date: new Date().toISOString().split("T")[0], title: "Hit protein target 3+ days", type: "protein" });
  }

  const sortedMilestones = milestones
    .filter((m) => m.date)
    .sort((a, b) => new Date(b.date) - new Date(a.date));

  return {
    totalMeals,
    loggedDays,
    currentStreak,
    achievements,
    milestones: sortedMilestones,
  };
}

export function AppProvider({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [allMeals, setAllMeals] = useState([]);
  const [todayMeals, setTodayMeals] = useState([]);
  const [weeklyMeals, setWeeklyMeals] = useState([]);
  const [activityMetrics, setActivityMetrics] = useState({
    totalMeals: 0,
    loggedDays: 0,
    currentStreak: 0,
    achievements: [],
    milestones: [],
  });
  const [loading, setLoading] = useState(true);
  const [mealsLoading, setMealsLoading] = useState(false);

  const getLocalMealsKey = () => `cf-local-meals-${user?.username || "anon"}`;

  const syncMealState = (meals) => {
    const normalizedMeals = (meals || [])
      .map((meal) => ({
        ...meal,
        id: meal.id || meal.timestamp,
      }))
      .sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0));

    setAllMeals(normalizedMeals);
    setTodayMeals(deriveTodayMeals(normalizedMeals));
    setWeeklyMeals(deriveWeeklyMeals(normalizedMeals));
    setActivityMetrics(deriveActivityMetrics(normalizedMeals));
  };

  const loadLocalMealsCache = () => {
    try {
      const raw = localStorage.getItem(getLocalMealsKey());
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  };

  const saveLocalMealsCache = (meals) => {
    try {
      localStorage.setItem(getLocalMealsKey(), JSON.stringify(meals || []));
    } catch {
      // no-op if storage is unavailable
    }
  };

  // Initialize auth and fetch user data
  useEffect(() => {
    const publicPaths = ["/", "/login", "/signup"];
    if (publicPaths.includes(pathname)) {
      setLoading(false);
      return;
    }

    const token = localStorage.getItem("token") || sessionStorage.getItem("token");
    if (!token) {
      router.push("/login");
      setLoading(false);
      return;
    }

    fetchUserData(token);
  }, [pathname, router]);

  const fetchUserData = async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/me`, {
        headers: {
          "Authorization": `Bearer ${token}`,
          "ngrok-skip-browser-warning": "true"
        }
      });
      const data = await response.json();
      
      if (!data.success) {
        router.push("/login");
        return;
      }

      setUser({
        username: data.username,
        token: token
      });
      setUserProfile(data.profile || {});
      
      await refreshMealData(token);
    } catch (error) {
      console.error("Failed to fetch user data:", error);
      router.push("/login");
    } finally {
      setLoading(false);
    }
  };

  const refreshMealData = async (token) => {
    const userToken = token || user?.token;
    if (!userToken) return;

    setMealsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/meals`, {
        headers: {
          "Authorization": `Bearer ${userToken}`,
          "ngrok-skip-browser-warning": "true"
        }
      });
      const parsed = await parseApiResponse(response, "Failed to load meals");

      if (parsed.ok && parsed.data?.success !== false) {
        const serverMeals = parsed.data?.meals || [];
        syncMealState(serverMeals);
        saveLocalMealsCache(serverMeals);
      } else if (isNotFoundError(parsed.error)) {
        const localMeals = loadLocalMealsCache();
        syncMealState(localMeals);
      }
    } catch (error) {
      console.error("Failed to refresh meals:", error);
      const localMeals = loadLocalMealsCache();
      syncMealState(localMeals);
    } finally {
      setMealsLoading(false);
    }
  };

  const fetchTodayMeals = async (token) => {
    await refreshMealData(token);
  };

  const fetchMealsByDate = async (date) => {
    return allMeals.filter((meal) => meal.date === date);
  };

  const fetchWeeklyMeals = async () => {
    await refreshMealData();
  };

  const addMeal = async (mealData) => {
    const token = user?.token;
    if (!token) return { success: false, error: "Not authenticated" };

    try {
      const response = await fetch(`${API_BASE_URL}/api/meals`, {
        method: 'POST',
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true"
        },
        body: JSON.stringify(mealData)
      });
      const parsed = await parseApiResponse(response, "Failed to save meal");
      
      if (parsed.ok && parsed.data?.success !== false) {
        await refreshMealData(token);
        return { success: true };
      }

      if (isNotFoundError(parsed.error)) {
        const fallbackMeal = {
          ...mealData,
          id: mealData.id || crypto.randomUUID(),
          timestamp: mealData.timestamp || new Date().toISOString(),
          date: mealData.date || new Date().toISOString().split("T")[0],
          source: "local-fallback",
        };
        const nextMeals = [fallbackMeal, ...allMeals];
        syncMealState(nextMeals);
        saveLocalMealsCache(nextMeals);
        return { success: true, warning: "Saved locally because backend meals route returned Not Found" };
      }

      return { success: false, error: parsed.error || "Failed to save meal" };
    } catch (error) {
      console.error("Failed to add meal:", error);
      const fallbackMeal = {
        ...mealData,
        id: mealData.id || crypto.randomUUID(),
        timestamp: mealData.timestamp || new Date().toISOString(),
        date: mealData.date || new Date().toISOString().split("T")[0],
        source: "local-fallback",
      };
      const nextMeals = [fallbackMeal, ...allMeals];
      syncMealState(nextMeals);
      saveLocalMealsCache(nextMeals);
      return {
        success: true,
        warning: `Saved locally: ${error.message || "Backend unavailable"}`,
      };
    }
  };

  const updateMeal = async (mealId, mealData) => {
    const token = user?.token;
    if (!token) return { success: false, error: "Not authenticated" };

    try {
      const response = await fetch(`${API_BASE_URL}/api/meals/${encodeURIComponent(mealId)}`, {
        method: "PUT",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true"
        },
        body: JSON.stringify(mealData)
      });
      const parsed = await parseApiResponse(response, "Failed to update meal");

      if (parsed.ok && parsed.data?.success !== false) {
        await refreshMealData(token);
        return { success: true };
      }
      return { success: false, error: parsed.error || "Failed to update meal" };
    } catch (error) {
      console.error("Failed to update meal:", error);
      return { success: false, error: error.message };
    }
  };

  const deleteMeal = async (mealId) => {
    const token = user?.token;
    if (!token) return { success: false, error: "Not authenticated" };

    try {
      const response = await fetch(`${API_BASE_URL}/api/meals/${encodeURIComponent(mealId)}`, {
        method: 'DELETE',
        headers: {
          "Authorization": `Bearer ${token}`,
          "ngrok-skip-browser-warning": "true"
        }
      });
      const parsed = await parseApiResponse(response, "Failed to delete meal");
      
      if (parsed.ok && parsed.data?.success !== false) {
        await refreshMealData(token);
        return { success: true };
      }
      return { success: false, error: parsed.error || "Failed to delete meal" };
    } catch (error) {
      console.error("Failed to delete meal:", error);
      return { success: false, error: error.message };
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    sessionStorage.removeItem("token");
    setUser(null);
    setUserProfile(null);
    setAllMeals([]);
    setTodayMeals([]);
    setWeeklyMeals([]);
    setActivityMetrics({
      totalMeals: 0,
      loggedDays: 0,
      currentStreak: 0,
      achievements: [],
      milestones: [],
    });
    router.push("/login");
  };

  const value = {
    user,
    userProfile,
    allMeals,
    todayMeals,
    weeklyMeals,
    activityMetrics,
    loading,
    mealsLoading,
    refreshMealData,
    fetchTodayMeals,
    fetchMealsByDate,
    fetchWeeklyMeals,
    addMeal,
    updateMeal,
    deleteMeal,
    logout,
    refreshUser: fetchUserData
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}
