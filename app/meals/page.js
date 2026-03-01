"use client";

import { useState } from "react";
import { useApp } from "../context/AppContext";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import Header from "../components/Header/Header";
import styles from "./meals.module.css";

export default function MealsPage() {
  const { user, todayMeals, mealsLoading, addMeal: addMealToContext, updateMeal: updateMealInContext, deleteMeal: deleteMealFromContext } = useApp();

  const [showAddModal, setShowAddModal] = useState(false);
  const [editingMealId, setEditingMealId] = useState(null);
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

  const totalDailyNutrition = todayMeals.reduce((acc, meal) => ({
    calories: acc.calories + (meal.total?.calories || 0),
    protein: acc.protein + (meal.total?.protein || 0),
    carbs: acc.carbs + (meal.total?.carbs || 0),
    fat: acc.fat + (meal.total?.fat || 0),
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

  const handleSaveMeal = async () => {
    if (newMeal.items.length === 0) return;

    const total = newMeal.items.reduce((acc, item) => ({
      calories: acc.calories + item.calories,
      protein: acc.protein + item.protein,
      carbs: acc.carbs + item.carbs,
      fat: acc.fat + item.fat,
    }), { calories: 0, protein: 0, carbs: 0, fat: 0 });

    const mealData = {
      type: newMeal.type,
      time: newMeal.time || new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      items: newMeal.items,
      total,
      timestamp: new Date().toISOString(),
      date: new Date().toISOString().split('T')[0]
    };

    const result = editingMealId
      ? await updateMealInContext(editingMealId, { ...mealData, id: editingMealId })
      : await addMealToContext(mealData);

    if (result.success) {
      setShowAddModal(false);
      setEditingMealId(null);
      setNewMeal({
        type: "Breakfast",
        time: "",
        items: []
      });
    } else {
      alert('Failed to save meal: ' + (result.error || 'Unknown error'));
    }
  };

  const handleEditMeal = (meal) => {
    setEditingMealId(meal.id || meal.timestamp);
    setNewMeal({
      type: meal.type || "Breakfast",
      time: meal.time || "",
      items: meal.items || [],
    });
    setShowAddModal(true);
  };

  const handleDeleteMeal = async (id) => {
    const result = await deleteMealFromContext(id);
    if (!result.success) {
      alert("Failed to delete meal: " + (result.error || "Unknown error"));
    }
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
        <Header title="Meal Logging" username={user?.username || ""} />
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
          <button className={styles.addMealButton} onClick={() => { setEditingMealId(null); setNewMeal({ type: "Breakfast", time: "", items: [] }); setShowAddModal(true); }}>
            <span className={styles.addIcon}>+</span>
            Log New Meal
          </button>

          {/* Meal List */}
          <div className={styles.mealsSection}>
            <h2 className={styles.mealsTitle}>Today&apos;s Meals</h2>
            {mealsLoading ? (
              <p className={styles.noMeals}>Loading meals...</p>
            ) : todayMeals.length === 0 ? (
              <p className={styles.noMeals}>No meals logged yet. Start by adding your first meal!</p>
            ) : (
              <div className={styles.mealsList}>
                {todayMeals.map((meal, index) => (
                  <div key={meal.timestamp || meal.id || index} className={styles.mealCard}>
                    <div className={styles.mealHeader}>
                      <div>
                        <h3 className={styles.mealType}>{meal.type}</h3>
                        <p className={styles.mealTime}>{meal.time}</p>
                      </div>
                      <div className={styles.mealActions}>
                        <button className={styles.deleteButton} onClick={() => handleEditMeal(meal)}>
                          ✏️
                        </button>
                        <button className={styles.deleteButton} onClick={() => handleDeleteMeal(meal.id || meal.timestamp)}>
                          🗑️
                        </button>
                      </div>
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
                        <span className={styles.nutrient}>🔥 {meal.total?.calories || 0} cal</span>
                        <span className={styles.nutrient}>💪 {meal.total?.protein || 0}g</span>
                        <span className={styles.nutrient}>🌾 {meal.total?.carbs || 0}g</span>
                        <span className={styles.nutrient}>🥑 {meal.total?.fat || 0}g</span>
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
                <button className={styles.modalClose} onClick={() => { setShowAddModal(false); setEditingMealId(null); }}>×</button>
                <h2 className={styles.modalTitle}>{editingMealId ? "Edit Meal" : "Log New Meal"}</h2>

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
                  <button className={styles.cancelButton} onClick={() => { setShowAddModal(false); setEditingMealId(null); }}>
                    Cancel
                  </button>
                  <button 
                    className={styles.saveButton} 
                    onClick={handleSaveMeal}
                    disabled={newMeal.items.length === 0}
                  >
                    {editingMealId ? "Update Meal" : "Save Meal"}
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
