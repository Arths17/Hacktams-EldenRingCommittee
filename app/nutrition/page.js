"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import Header from "../components/Header/Header";
import styles from "./nutrition.module.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function NutritionPage() {
  const router = useRouter();
  const [username, setUsername] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedFood, setSelectedFood] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dailyGoals, setDailyGoals] = useState({
    calories: 2400,
    protein_g: 108,
    carbs_g: 275,
    fat_g: 90,
    fiber_g: 38,
  });

  useEffect(() => {
    const token = localStorage.getItem("token") || sessionStorage.getItem("token");
    if (!token) { 
      router.push("/login"); 
      return; 
    }
    fetch(`${API_BASE_URL}/api/me`, {
      headers: { "Authorization": `Bearer ${token}`, "ngrok-skip-browser-warning": "true" },
    })
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) {
          router.push("/login");
        } else {
          setUsername(data.username);
        }
      })
      .catch(() => router.push("/login"));
  }, [router]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setLoading(true);
    setSelectedFood(null);
    try {
      const token = localStorage.getItem("token") || sessionStorage.getItem("token");
      const response = await fetch(`${API_BASE_URL}/api/nutrition/search?q=${encodeURIComponent(searchQuery)}&limit=20`, {
        headers: { 
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true",
        },
      });

      const data = await response.json();
      if (data.success) {
        setSearchResults(data.results || []);
        if ((data.results || []).length === 0) setError("No foods found. Try a different search term.");
        else setError("");
      } else {
        setError(data.error || "Search failed.");
        setSearchResults([]);
      }
    } catch (error) {
      console.error("Search error:", error);
      setError("Could not reach server.");
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };

  const viewFoodDetails = async (food) => {
    setSelectedFood(food); // show immediately with what we have
    try {
      const token = localStorage.getItem("token") || sessionStorage.getItem("token");
      const res = await fetch(`${API_BASE_URL}/api/nutrition/food/${food.fdc_id}`, {
        headers: {
          "Authorization": `Bearer ${token}`,
          "ngrok-skip-browser-warning": "true",
        },
      });
      const data = await res.json();
      if (data.success) setSelectedFood(data.food);
    } catch (_) {}
  };

  return (
    <div className={styles.layout}>
      <div className={`${styles.orb} ${styles.orbGreen}`} />
      <div className={`${styles.orb} ${styles.orbGold}`} />
      
      <CampusFuelNav />
      <div className={styles.main}>
        <Header title="Nutrition Database" username={username || ""} />
        <div className={styles.content}>

          {/* Daily Goals Overview */}
          <div className={styles.goalsCard}>
            <h2 className={styles.goalsTitle}>📊 Your Daily Goals</h2>
            <div className={styles.goalsGrid}>
              <div className={styles.goalItem}>
                <span className={styles.goalIcon}>🔥</span>
                <span className={styles.goalLabel}>Calories</span>
                <span className={styles.goalValue}>{dailyGoals.calories} kcal</span>
              </div>
              <div className={styles.goalItem}>
                <span className={styles.goalIcon}>💪</span>
                <span className={styles.goalLabel}>Protein</span>
                <span className={styles.goalValue}>{dailyGoals.protein_g}g</span>
              </div>
              <div className={styles.goalItem}>
                <span className={styles.goalIcon}>🌾</span>
                <span className={styles.goalLabel}>Carbs</span>
                <span className={styles.goalValue}>{dailyGoals.carbs_g}g</span>
              </div>
              <div className={styles.goalItem}>
                <span className={styles.goalIcon}>🥑</span>
                <span className={styles.goalLabel}>Fat</span>
                <span className={styles.goalValue}>{dailyGoals.fat_g}g</span>
              </div>
              <div className={styles.goalItem}>
                <span className={styles.goalIcon}>🥦</span>
                <span className={styles.goalLabel}>Fiber</span>
                <span className={styles.goalValue}>{dailyGoals.fiber_g}g</span>
              </div>
            </div>
          </div>

          {/* Search Section */}
          <div className={styles.searchCard}>
            <h2 className={styles.searchTitle}>🔍 Search Foods</h2>
            <form onSubmit={handleSearch} className={styles.searchForm}>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search for foods (e.g., chicken breast, apple, rice)..."
                className={styles.searchInput}
              />
              <button type="submit" className={styles.searchButton} disabled={loading}>
                {loading ? "Searching..." : "Search"}
              </button>
            </form>
          </div>

          {/* Search Results */}
          {error && <p className={styles.searchError}>{error}</p>}
          {searchResults.length > 0 && (
            <div className={styles.resultsCard}>
              <h3 className={styles.resultsTitle}>Search Results <span className={styles.resultsCount}>({searchResults.length})</span></h3>
              <div className={styles.resultsList}>
                {searchResults.map((food, idx) => (
                  <div key={idx} className={styles.resultItem} onClick={() => viewFoodDetails(food)}>
                    <div className={styles.resultMain}>
                      <h4 className={styles.resultName}>{food.name}</h4>
                      <p className={styles.resultCategory}>{food.category || food.source || 'Uncategorized'}</p>
                    </div>
                    <div className={styles.resultNutrients}>
                      {food.calories != null && <span className={styles.nutrientBadge}>🔥 {food.calories} kcal</span>}
                      {food.protein_g != null && <span className={styles.nutrientBadge}>💪 {food.protein_g}g protein</span>}
                      {food.carbs_g != null && <span className={styles.nutrientBadge}>🌾 {food.carbs_g}g carbs</span>}
                    </div>
                    <button className={styles.viewButton}>View →</button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Food Details Modal */}
          {selectedFood && (
            <div className={styles.modal} onClick={() => setSelectedFood(null)}>
              <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
                <button className={styles.modalClose} onClick={() => setSelectedFood(null)}>×</button>
                <h2 className={styles.modalTitle}>{selectedFood.name}</h2>
                <div className={styles.modalMeta}>
                  {selectedFood.category && <span className={styles.modalTag}>{selectedFood.category}</span>}
                  {selectedFood.source && <span className={styles.modalTag}>{selectedFood.source}</span>}
                </div>
                {selectedFood.serving && (
                  <p className={styles.modalServing}>
                    📏 Serving: {selectedFood.serving.amount} {selectedFood.serving.unit} ({selectedFood.serving.grams}g)
                  </p>
                )}

                <div className={styles.nutrientDetails}>
                  <h3 className={styles.detailsSubtitle}>Nutrition Facts <span style={{fontWeight:400,fontSize:'0.8em'}}>(per 100g)</span></h3>

                  {/* Macro highlights */}
                  <div className={styles.macroRow}>
                    {[
                      { label: "Calories", val: selectedFood.calories, unit: "kcal", icon: "🔥" },
                      { label: "Protein", val: selectedFood.protein_g, unit: "g", icon: "💪" },
                      { label: "Carbs", val: selectedFood.carbs_g, unit: "g", icon: "🌾" },
                      { label: "Fat", val: selectedFood.fat_g, unit: "g", icon: "🥑" },
                    ].filter(m => m.val != null).map(m => (
                      <div key={m.label} className={styles.macroPill}>
                        <span className={styles.macroIcon}>{m.icon}</span>
                        <span className={styles.macroVal}>{m.val}{m.unit}</span>
                        <span className={styles.macroLabel}>{m.label}</span>
                      </div>
                    ))}
                  </div>

                  {/* Full nutrient table */}
                  <div className={styles.nutrientGrid}>
                    {[
                      { label: "Fiber", val: selectedFood.fiber_g, unit: "g" },
                      { label: "Sugar", val: selectedFood.sugar_g, unit: "g" },
                      { label: "Saturated Fat", val: selectedFood.sat_fat_g, unit: "g" },
                      { label: "Trans Fat", val: selectedFood.trans_fat_g, unit: "g" },
                      { label: "Cholesterol", val: selectedFood.cholesterol_mg, unit: "mg" },
                      { label: "Sodium", val: selectedFood.sodium_mg, unit: "mg" },
                      { label: "Potassium", val: selectedFood.potassium_mg, unit: "mg" },
                      { label: "Calcium", val: selectedFood.calcium_mg, unit: "mg" },
                      { label: "Iron", val: selectedFood.iron_mg, unit: "mg" },
                      { label: "Zinc", val: selectedFood.zinc_mg, unit: "mg" },
                      { label: "Vitamin C", val: selectedFood.vitamin_c_mg, unit: "mg" },
                      { label: "Vitamin D", val: selectedFood.vitamin_d_mcg, unit: "µg" },
                      { label: "Vitamin A", val: selectedFood.vitamin_a_mcg, unit: "µg" },
                    ].filter(r => r.val != null).map(r => (
                      <div key={r.label} className={styles.nutrientRow}>
                        <span className={styles.nutrientName}>{r.label}</span>
                        <span className={styles.nutrientValue}>{r.val} {r.unit}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Educational Tips */}
          <div className={styles.tipsCard}>
            <h3 className={styles.tipsTitle}>💡 Nutrition Tips</h3>
            <div className={styles.tipsList}>
              <div className={styles.tip}>
                <span className={styles.tipIcon}>🥛</span>
                <p className={styles.tipText}>Aim for 0.8-1g of protein per kg of body weight daily for maintenance.</p>
              </div>
              <div className={styles.tip}>
                <span className={styles.tipIcon}>🥦</span>
                <p className={styles.tipText}>Fill half your plate with vegetables for optimal fiber and micronutrient intake.</p>
              </div>
              <div className={styles.tip}>
                <span className={styles.tipIcon}>💧</span>
                <p className={styles.tipText}>Drink at least 8 glasses of water daily for proper hydration.</p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
