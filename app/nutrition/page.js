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
  const [dailyGoals, setDailyGoals] = useState({
    calories: 2400,
    protein_g: 108,
    carbs_g: 275,
    fat_g: 90,
    fiber_g: 38,
  });

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { 
      router.push("/login"); 
      return; 
    }
    fetch(`${API_BASE_URL}/api/me`, {
      headers: { "Authorization": `Bearer ${token}` },
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
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE_URL}/api/nutrition/search?q=${encodeURIComponent(searchQuery)}`, {
        headers: { 
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();
      if (data.success) {
        setSearchResults(data.results || []);
      } else {
        console.error("Search failed:", data.error);
        setSearchResults([]);
      }
    } catch (error) {
      console.error("Search error:", error);
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };

  const viewFoodDetails = (food) => {
    setSelectedFood(food);
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
          {searchResults.length > 0 && (
            <div className={styles.resultsCard}>
              <h3 className={styles.resultsTitle}>Search Results</h3>
              <div className={styles.resultsList}>
                {searchResults.map((food, idx) => (
                  <div key={idx} className={styles.resultItem} onClick={() => viewFoodDetails(food)}>
                    <div className={styles.resultMain}>
                      <h4 className={styles.resultName}>{food.name || food.food_name}</h4>
                      <p className={styles.resultCategory}>{food.category || 'Uncategorized'}</p>
                    </div>
                    <div className={styles.resultNutrients}>
                      <span className={styles.nutrientBadge}>🔥 {food.calories || 0} cal</span>
                      <span className={styles.nutrientBadge}>💪 {food.protein_g || 0}g</span>
                    </div>
                    <button className={styles.viewButton}>View Details</button>
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
                <h2 className={styles.modalTitle}>{selectedFood.name || selectedFood.food_name}</h2>
                <p className={styles.modalCategory}>{selectedFood.category || 'Uncategorized'}</p>
                
                <div className={styles.nutrientDetails}>
                  <h3 className={styles.detailsSubtitle}>Nutritional Information (per 100g)</h3>
                  <div className={styles.nutrientGrid}>
                    <div className={styles.nutrientRow}>
                      <span className={styles.nutrientName}>Calories</span>
                      <span className={styles.nutrientValue}>{selectedFood.calories || 0} kcal</span>
                    </div>
                    <div className={styles.nutrientRow}>
                      <span className={styles.nutrientName}>Protein</span>
                      <span className={styles.nutrientValue}>{selectedFood.protein_g || 0}g</span>
                    </div>
                    <div className={styles.nutrientRow}>
                      <span className={styles.nutrientName}>Carbohydrates</span>
                      <span className={styles.nutrientValue}>{selectedFood.carbs_g || 0}g</span>
                    </div>
                    <div className={styles.nutrientRow}>
                      <span className={styles.nutrientName}>Fat</span>
                      <span className={styles.nutrientValue}>{selectedFood.fat_g || 0}g</span>
                    </div>
                    {selectedFood.fiber_g && (
                      <div className={styles.nutrientRow}>
                        <span className={styles.nutrientName}>Fiber</span>
                        <span className={styles.nutrientValue}>{selectedFood.fiber_g}g</span>
                      </div>
                    )}
                    {selectedFood.sugar_g && (
                      <div className={styles.nutrientRow}>
                        <span className={styles.nutrientName}>Sugar</span>
                        <span className={styles.nutrientValue}>{selectedFood.sugar_g}g</span>
                      </div>
                    )}
                    {selectedFood.iron_mg && (
                      <div className={styles.nutrientRow}>
                        <span className={styles.nutrientName}>Iron</span>
                        <span className={styles.nutrientValue}>{selectedFood.iron_mg}mg</span>
                      </div>
                    )}
                    {selectedFood.calcium_mg && (
                      <div className={styles.nutrientRow}>
                        <span className={styles.nutrientName}>Calcium</span>
                        <span className={styles.nutrientValue}>{selectedFood.calcium_mg}mg</span>
                      </div>
                    )}
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
