"use client";

import { useEffect, useState } from "react";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import Header from "../components/Header/Header";
import { useApp } from "../context/AppContext";
import styles from "./workout.module.css";

const WORKOUT_TYPES = ["Strength", "Cardio", "Sports", "Yoga", "HIIT", "Other"];

export default function WorkoutPage() {
  const { user, workouts, workoutsLoading, fetchWorkouts, addWorkout, deleteWorkout } = useApp();
  const [type, setType] = useState("Strength");
  const [duration, setDuration] = useState(30);
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (user?.token) fetchWorkouts(user.token);
  }, [user?.token]);

  const handleAddWorkout = async () => {
    const entry = {
      id: crypto.randomUUID(),
      type,
      duration: Number(duration) || 0,
      notes: notes.trim(),
      date: new Date().toISOString().split("T")[0],
      timestamp: new Date().toISOString(),
    };
    const result = await addWorkout(entry);
    if (!result.success) {
      alert(result.error || "Failed to save workout");
      return;
    }
    setNotes("");
    setDuration(30);
    setType("Strength");
  };

  const handleDeleteWorkout = async (id) => {
    if (!window.confirm("Delete this workout log?")) return;
    const result = await deleteWorkout(id);
    if (!result.success) {
      alert(result.error || "Failed to delete workout");
    }
  };

  const weeklyMinutes = workouts
    .filter((l) => {
      const d = new Date(l.date);
      const now = new Date();
      const diff = (now - d) / (1000 * 60 * 60 * 24);
      return diff >= 0 && diff <= 6;
    })
    .reduce((sum, l) => sum + (Number(l.duration) || 0), 0);

  return (
    <div className={styles.layout}>
      <CampusFuelNav />
      <div className={styles.main}>
        <Header title="Workout Tracker" username={user?.username || ""} />
        <div className={styles.content}>
          <div className={styles.card}>
            <h2 className={styles.title}>Log Workout</h2>
            <div className={styles.row}>
              <select className={styles.input} value={type} onChange={(e) => setType(e.target.value)}>
                {WORKOUT_TYPES.map((workoutType) => (
                  <option key={workoutType}>{workoutType}</option>
                ))}
              </select>
              <input
                className={styles.input}
                type="number"
                min="5"
                max="300"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                placeholder="Duration (min)"
              />
            </div>
            <textarea
              className={styles.textarea}
              rows={3}
              placeholder="Notes (optional)"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <button className={styles.btn} type="button" onClick={handleAddWorkout}>Save Workout</button>
            <p className={styles.meta}>Weekly total: <strong>{weeklyMinutes} min</strong></p>
          </div>

          <div className={styles.card}>
            <h2 className={styles.title}>Workout History</h2>
            {workoutsLoading ? (
              <p className={styles.empty}>Loading workouts...</p>
            ) : workouts.length === 0 ? (
              <p className={styles.empty}>No workouts logged yet.</p>
            ) : (
              <div className={styles.list}>
                {workouts.map((log) => (
                  <div key={log.id} className={styles.item}>
                    <div>
                      <p className={styles.itemTitle}>{log.type} · {log.duration} min</p>
                      <p className={styles.itemMeta}>{log.date}{log.notes ? ` · ${log.notes}` : ""}</p>
                    </div>
                    <button className={styles.delete} type="button" onClick={() => handleDeleteWorkout(log.id)}>Delete</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
