import styles from "./MealLog.module.css";

const meals = [
  {
    id: 1,
    name: "Scrambled Eggs & Toast",
    type: "Breakfast",
    time: "7:30 AM",
    calories: 420,
    protein: 22,
    carbs: 38,
    fat: 18,
    icon: "🍳",
  },
  {
    id: 2,
    name: "Grilled Chicken Bowl",
    type: "Lunch",
    time: "12:15 PM",
    calories: 680,
    protein: 48,
    carbs: 55,
    fat: 16,
    icon: "🥗",
  },
  {
    id: 3,
    name: "Protein Bar",
    type: "Snack",
    time: "3:00 PM",
    calories: 210,
    protein: 20,
    carbs: 22,
    fat: 7,
    icon: "🍫",
  },
  {
    id: 4,
    name: "Pasta Primavera",
    type: "Dinner",
    time: "7:00 PM",
    calories: 590,
    protein: 18,
    carbs: 82,
    fat: 14,
    icon: "🍝",
  },
];

const mealTypeColors = {
  Breakfast: "#145A32",
  Lunch: "#C99B4C",
  Snack: "#5b8dee",
  Dinner: "#e05a5a",
};

export default function MealLog() {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Today&apos;s Meal Log</h2>
        <a href="/meals" className={styles.addBtn}>+ Add Meal</a>
      </div>
      <div className={styles.list}>
        {meals.map((meal) => (
          <div key={meal.id} className={styles.row}>
            <div className={styles.iconCol}>
              <span className={styles.icon}>{meal.icon}</span>
            </div>
            <div className={styles.info}>
              <span className={styles.mealName}>{meal.name}</span>
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
                <span className={styles.macroVal}>{meal.protein}g</span>
              </span>
              <span className={styles.macro}>
                <span className={styles.macroLabel}>Carbs</span>
                <span className={styles.macroVal}>{meal.carbs}g</span>
              </span>
              <span className={styles.macro}>
                <span className={styles.macroLabel}>Fat</span>
                <span className={styles.macroVal}>{meal.fat}g</span>
              </span>
            </div>
            <div className={styles.calories}>
              <span className={styles.calVal}>{meal.calories}</span>
              <span className={styles.calLabel}>kcal</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
