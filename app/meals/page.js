"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import Header from "../components/Header/Header";
import styles from "./meals.module.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function MealsPage() {
  const router = useRouter();
  const [username, setUsername] = useState(null);
  const [meals, setMeals] = useState([
    {
      id: 1,
      type: "Breakfast",
      time: "8:30 AM",
      items: [
        { name: "Oatmeal with berries", calories: 320, protein: 12, carbs: 54, fat: 6 },
        { name: "Greek yogurt", calories: 150, protein: 15, carbs: 8, fat: 4 },
      ],
      total: { calories: 470, protein: 27, carbs: 62, fat: 10 }
    },
    {
      id: 2,
      type: "Lunch",
      time: "1:00 PM",
      items: [
        { name: "Grilled chicken breast", calories: 280, protein: 53, carbs: 0, fat: 6 },
        { name: "Brown rice", calories: 215, protein: 5, carbs: 45, fat: 2 },
        { name: "Mixed vegetables", calories: 80, protein: 3, carbs: 15, fat: 1 },
      ],
      total: { calories: 575, protein: 61, carbs: 60, fat: 9 }
    },
    {
      id: 3,
      type: "Dinner",
      time: "7:00 PM",
      items: [
        { name: "Salmon fillet", calories: 367, protein: 39, carbs: 0, fat: 22 },
        { name: "Sweet potato", calories: 180, protein: 4, carbs: 41, fat: 0 },
        { name: "Broccoli", calories: 55, protein: 4, carbs: 11, fat: 1 },
      ],
      total: { calories: 602, protein: 47, carbs: 52, fat: 23 }
    },
  ]);

  const [showAddModal, setShowAddModal] = useState(false);
  const [newMeal, setNewMeal] = useState({
    type: "Breakfast",
    time: "",
    items: []
  });
  const [newItem, setNewItem] = useState({
    name: "",
    calories: "",
    protein: "",
    carbs: "",
    fat: ""
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

  const totalDailyNutrition = meals.reduce((acc, meal) => ({
    calories: acc.calories + meal.total.calories,
    protein: acc.protein + meal.total.protein,
    carbs: acc.carbs + meal.total.carbs,
    fat: acc.fat + meal.total.fat,
  }), { calories: 0, protein: 0, carbs: 0, fat: 0 });

  const handleAddItem = () => {
    if (!newItem.name || !newItem.calories) return;
    
    const item = {
      name: newItem.name,
      calories: parseInt(newItem.calories) || 0,
      protein: parseInt(newItem.protein) || 0,
      carbs: parseInt(newItem.carbs) || 0,
      fat: parseInt(newItem.fat) || 0,
    };

    setNewMeal({
      ...newMeal,
      items: [...newMeal.items, item]
    });

    setNewItem({
      name: "",
      calories: "",
      protein: "",
      carbs: "",
      fat: ""
    });
  };

  const handleSaveMeal = () => {
    if (newMeal.items.length === 0) return;

    const total = newMeal.items.reduce((acc, item) => ({
      calories: acc.calories + item.calories,
      protein: acc.protein + item.protein,
      carbs: acc.carbs + item.carbs,
      fat: acc.fat + item.fat,
    }), { calories: 0, protein: 0, carbs: 0, fat: 0 });

    const meal = {
      id: meals.length + 1,
      type: newMeal.type,
      time: newMeal.time || new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      items: newMeal.items,
      total
    };

    setMeals([...meals, meal]);
    setShowAddModal(false);
    setNewMeal({
      type: "Breakfast",
      time: "",
      items: []
    });
  };

  const deleteMeal = (id) => {
    setMeals(meals.filter(m => m.id !== id));
  };

  const goals = {
    calories: 2400,
    protein: 108,
    carbs: 275,
    fat: 90
  };

  const dailyProgress = {
    calories: Math.round((totalDailyNutrition.calories / goals.calories) * 100),
    protein: Math.round((totalDailyNutrition.protein / goals.protein) * 100),
    carbs: Math.round((totalDailyNutrition.carbs / goals.carbs) * 100),
    fat: Math.round((totalDailyNutrition.fat / goals.fat) * 100),
  };

  return (
    <div className={styles.layout}>
      <div className={`${styles.orb} ${styles.orbGreen}`} />
      <div className={`${styles.orb} ${styles.orbGold}`} />
      
      <CampusFuelNav />
      <div className={styles.main}>
        <Header title="Meal Logging" username={username || ""} />
        <div className={styles.content}>

          {/* Daily Summary */}
          <div className={styles.summaryCard}>
            <h2 className={styles.summaryTitle}>📊 Today&apos;s Summary</h2>
            <div className={styles.summaryGrid}>
              <div className={styles.summaryItem}>
                <div className={styles.summaryHeader}>
                  <span className={styles.summaryIcon}>🔥</span>
                  <span className={styles.summaryLabel}>Calories</span>
                </div>
                <div className={styles.summaryValues}>
                  <span className={styles.summaryValue}>{totalDailyNutrition.calories}</span>
                  <span className={styles.summaryGoal}>/ {goals.calories}</span>
                </div>
                <div className={styles.progressBar}>
                  <div className={styles.progressFill} style={{ width: `${Math.min(dailyProgress.calories, 100)}%` }} />
                </div>
              </div>

              <div className={styles.summaryItem}>
                <div className={styles.summaryHeader}>
                  <span className={styles.summaryIcon}>💪</span>
                  <span className={styles.summaryLabel}>Protein</span>
                </div>
                <div className={styles.summaryValues}>
                  <span className={styles.summaryValue}>{totalDailyNutrition.protein}g</span>
                  <span className={styles.summaryGoal}>/ {goals.protein}g</span>
                </div>
                <div className={styles.progressBar}>
                  <div className={`${styles.progressFill} ${styles.progressProtein}`} style={{ width: `${Math.min(dailyProgress.protein, 100)}%` }} />
                </div>
              </div>

              <div className={styles.summaryItem}>
                <div className={styles.summaryHeader}>
                  <span className={styles.summaryIcon}>🌾</span>
                  <span className={styles.summaryLabel}>Carbs</span>
                </div>
                <div className={styles.summaryValues}>
                  <span className={styles.summaryValue}>{totalDailyNutrition.carbs}g</span>
                  <span className={styles.summaryGoal}>/ {goals.carbs}g</span>
                </div>
                <div className={styles.progressBar}>
                  <div className={`${styles.progressFill} ${styles.progressCarbs}`} style={{ width: `${Math.min(dailyProgress.carbs, 100)}%` }} />
                </div>
              </div>

              <div className={styles.summaryItem}>
                <div className={styles.summaryHeader}>
                  <span className={styles.summaryIcon}>🥑</span>
                  <span className={styles.summaryLabel}>Fat</span>
                </div>
                <div className={styles.summaryValues}>
                  <span className={styles.summaryValue}>{totalDailyNutrition.fat}g</span>
                  <span className={styles.summaryGoal}>/ {goals.fat}g</span>
                </div>
                <div className={styles.progressBar}>
                  <div className={`${styles.progressFill} ${styles.progressFat}`} style={{ width: `${Math.min(dailyProgress.fat, 100)}%` }} />
                </div>
              </div>
            </div>
          </div>

          {/* Add Meal Button */}
          <button className={styles.addMealButton} onClick={() => setShowAddModal(true)}>
            <span className={styles.addIcon}>+</span>
            Log New Meal
          </button>

          {/* Meal List */}
          <div className={styles.mealsSection}>
            <h2 className={styles.mealsTitle}>Today&apos;s Meals</h2>
            {meals.length === 0 ? (
              <p className={styles.noMeals}>No meals logged yet. Start by adding your first meal!</p>
            ) : (
              <div className={styles.mealsList}>
                {meals.map((meal) => (
                  <div key={meal.id} className={styles.mealCard}>
                    <div className={styles.mealHeader}>
                      <div>
                        <h3 className={styles.mealType}>{meal.type}</h3>
                        <p className={styles.mealTime}>{meal.time}</p>
                      </div>
                      <button className={styles.deleteButton} onClick={() => deleteMeal(meal.id)}>
                        🗑️
                      </button>
                    </div>
                    <div className={styles.mealItems}>
                      {meal.items.map((item, idx) => (
                        <div key={idx} className={styles.mealItem}>
                          <span className={styles.itemName}>{item.name}</span>
                          <span className={styles.itemCalories}>{item.calories} cal</span>
                        </div>
                      ))}
                    </div>
                    <div className={styles.mealTotal}>
                      <span className={styles.totalLabel}>Total:</span>
                      <div className={styles.totalNutrients}>
                        <span className={styles.nutrient}>🔥 {meal.total.calories} cal</span>
                        <span className={styles.nutrient}>💪 {meal.total.protein}g</span>
                        <span className={styles.nutrient}>🌾 {meal.total.carbs}g</span>
                        <span className={styles.nutrient}>🥑 {meal.total.fat}g</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Add Meal Modal */}
          {showAddModal && (
            <div className={styles.modal} onClick={() => setShowAddModal(false)}>
              <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
                <button className={styles.modalClose} onClick={() => setShowAddModal(false)}>×</button>
                <h2 className={styles.modalTitle}>Log New Meal</h2>

                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>Meal Type</label>
                  <select 
                    className={styles.formSelect}
                    value={newMeal.type}
                    onChange={(e) => setNewMeal({ ...newMeal, type: e.target.value })}
                  >
                    <option>Breakfast</option>
                    <option>Lunch</option>
                    <option>Dinner</option>
                    <option>Snack</option>
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>Time (optional)</label>
                  <input 
                    type="time"
                    className={styles.formInput}
                    value={newMeal.time}
                    onChange={(e) => setNewMeal({ ...newMeal, time: e.target.value })}
                  />
                </div>

                <div className={styles.addItemSection}>
                  <h3 className={styles.addItemTitle}>Add Food Items</h3>
                  <div className={styles.itemForm}>
                    <input
                      type="text"
                      placeholder="Food name"
                      className={styles.formInput}
                      value={newItem.name}
                      onChange={(e) => setNewItem({ ...newItem, name: e.target.value })}
                    />
                    <div className={styles.nutrientInputs}>
                      <input
                        type="number"
                        placeholder="Calories"
                        className={styles.formInputSmall}
                        value={newItem.calories}
                        onChange={(e) => setNewItem({ ...newItem, calories: e.target.value })}
                      />
                      <input
                        type="number"
                        placeholder="Protein (g)"
                        className={styles.formInputSmall}
                        value={newItem.protein}
                        onChange={(e) => setNewItem({ ...newItem, protein: e.target.value })}
                      />
                      <input
                        type="number"
                        placeholder="Carbs (g)"
                        className={styles.formInputSmall}
                        value={newItem.carbs}
                        onChange={(e) => setNewItem({ ...newItem, carbs: e.target.value })}
                      />
                      <input
                        type="number"
                        placeholder="Fat (g)"
                        className={styles.formInputSmall}
                        value={newItem.fat}
                        onChange={(e) => setNewItem({ ...newItem, fat: e.target.value })}
                      />
                    </div>
                    <button className={styles.addItemButton} onClick={handleAddItem}>Add Item</button>
                  </div>

                  {newMeal.items.length > 0 && (
                    <div className={styles.itemsList}>
                      <h4 className={styles.itemsListTitle}>Items ({newMeal.items.length})</h4>
                      {newMeal.items.map((item, idx) => (
                        <div key={idx} className={styles.addedItem}>
                          <span>{item.name}</span>
                          <span>{item.calories} cal</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className={styles.modalActions}>
                  <button className={styles.cancelButton} onClick={() => setShowAddModal(false)}>
                    Cancel
                  </button>
                  <button 
                    className={styles.saveButton} 
                    onClick={handleSaveMeal}
                    disabled={newMeal.items.length === 0}
                  >
                    Save Meal
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
