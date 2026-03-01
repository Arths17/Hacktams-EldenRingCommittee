"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./survey.module.css";

const STEPS = [
  {
    key: "name",
    emoji: "👋",
    question: "What's your name?",
    type: "text",
    placeholder: "e.g. Jordan",
  },
  {
    key: "age",
    emoji: "🎂",
    question: "How old are you?",
    type: "text",
    placeholder: "e.g. 20",
  },
  {
    key: "gender",
    emoji: "⚧",
    question: "What's your gender?",
    type: "select",
    options: ["Male", "Female", "Non-binary", "Prefer not to say"],
  },
  {
    key: "height",
    emoji: "📏",
    question: "What's your height?",
    type: "text",
    placeholder: "e.g. 5'10\" or 178cm",
  },
  {
    key: "weight",
    emoji: "⚖️",
    question: "What's your weight?",
    type: "text",
    placeholder: "e.g. 160 lbs or 73 kg",
  },
  {
    key: "goal",
    emoji: "🎯",
    question: "What's your body goal?",
    type: "select",
    options: ["Fat loss", "Muscle gain", "Maintenance", "General health"],
  },
  {
    key: "diet_type",
    emoji: "🥗",
    question: "What's your diet type?",
    type: "select",
    options: ["Omnivore", "Vegetarian", "Vegan", "Halal", "Kosher", "Other"],
  },
  {
    key: "allergies",
    emoji: "⚠️",
    question: "Any food allergies or intolerances?",
    type: "text",
    placeholder: "e.g. peanuts, gluten — or 'none'",
  },
  {
    key: "budget",
    emoji: "💰",
    question: "What's your food budget level?",
    type: "select",
    options: ["Low", "Medium", "Flexible"],
  },
  {
    key: "cooking_access",
    emoji: "🍳",
    question: "What cooking access do you have?",
    type: "select",
    options: ["Dorm microwave", "Shared kitchen", "Full kitchen", "None"],
  },
  {
    key: "cultural_prefs",
    emoji: "🌍",
    question: "Any cultural food preferences?",
    type: "text",
    placeholder: "e.g. South Asian, Mediterranean — or 'none'",
  },
  {
    key: "class_schedule",
    emoji: "📅",
    question: "What's your class schedule?",
    type: "text",
    placeholder: "e.g. MWF 8am–2pm, TTh 10am–4pm",
  },
  {
    key: "sleep_schedule",
    emoji: "😴",
    question: "When do you sleep and wake up?",
    type: "text",
    placeholder: "e.g. 11pm–7am or 2am–9am",
  },
  {
    key: "workout_times",
    emoji: "🏋️",
    question: "When do you work out?",
    type: "text",
    placeholder: "e.g. MWF 5pm — or 'none'",
  },
  {
    key: "stress_level",
    emoji: "😰",
    question: "What's your stress level right now?",
    type: "slider",
    min: 1,
    max: 10,
    labels: ["1 – Totally chill", "10 – Overwhelmed"],
  },
  {
    key: "energy_level",
    emoji: "⚡",
    question: "What's your energy level right now?",
    type: "slider",
    min: 1,
    max: 10,
    labels: ["1 – Exhausted", "10 – Energized"],
  },
  {
    key: "sleep_quality",
    emoji: "🌙",
    question: "How's your sleep quality been lately?",
    type: "select",
    options: ["Poor", "Okay", "Good"],
  },
  {
    key: "mood",
    emoji: "💭",
    question: "How's your mood today?",
    type: "select",
    options: ["Low", "Neutral", "Good"],
  },
  {
    key: "extra",
    emoji: "📝",
    question: "Anything else we should know?",
    type: "textarea",
    placeholder: "Health conditions, habits, concerns — or 'none'",
  },
];

const DAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
const WORKOUT_SLOTS = ["Morning","Afternoon","Evening","Night","I don't work out"];

export default function SurveyPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [current, setCurrent] = useState("");
  // daypicker state: array of selected day strings
  const [selectedDays, setSelectedDays] = useState([]);
  // sleeppicker state
  const [bedTime, setBedTime] = useState("");
  const [wakeTime, setWakeTime] = useState("");
  // workoutpicker state
  const [workoutDays, setWorkoutDays] = useState([]);
  const [workoutSlot, setWorkoutSlot] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const q = STEPS[step];
  const isLast = step === STEPS.length - 1;

  function handleNext() {
    // Serialize interactive pickers into a string value
    let val = current.trim();
    if (q.type === "daypicker") {
      val = selectedDays.length > 0 ? selectedDays.join(", ") : "";
    } else if (q.type === "sleeppicker") {
      val = bedTime && wakeTime ? `sleep ${bedTime}, wake ${wakeTime}` : "";
    } else if (q.type === "workoutpicker") {
      if (workoutSlot === "i don't work out") val = "none";
      else val = workoutDays.length > 0 && workoutSlot ? `${workoutDays.join(", ")} – ${workoutSlot}` : "";
    } else {
      val = current.trim() || (q.type === "slider" ? "5" : "");
    }
    if (!val) {
      setError("Please make a selection before continuing.");
      return;
    }
    setError("");
    const updated = { ...answers, [q.key]: val.toLowerCase() };
    setAnswers(updated);

    if (isLast) {
      submitProfile(updated);
    } else {
      const nextKey = STEPS[step + 1].key;
      const nextType = STEPS[step + 1].type;
      const saved = updated[nextKey] || "";
      if (nextType === "daypicker") {
        setSelectedDays(saved ? saved.split(", ") : []);
      } else if (nextType === "sleeppicker") {
        const m = saved.match(/sleep (.+), wake (.+)/);
        setBedTime(m ? m[1] : ""); setWakeTime(m ? m[2] : "");
      } else if (nextType === "workoutpicker") {
        if (saved === "none") { setWorkoutDays([]); setWorkoutSlot("i don't work out"); }
        else {
          const parts = saved.split(" – ");
          setWorkoutDays(parts[0] ? parts[0].split(", ") : []);
          setWorkoutSlot(parts[1] || "");
        }
      } else {
        setCurrent(saved || (STEPS[step + 1].type === "slider" ? "5" : ""));
      }
      setStep((s) => s + 1);
    }
  }

  function handleBack() {
    setError("");
    const prevKey = STEPS[step - 1].key;
    const prevType = STEPS[step - 1].type;
    const saved = answers[prevKey] || "";
    if (prevType === "daypicker") {
      setSelectedDays(saved ? saved.split(", ") : []);
    } else if (prevType === "sleeppicker") {
      const m = saved.match(/sleep (.+), wake (.+)/);
      setBedTime(m ? m[1] : ""); setWakeTime(m ? m[2] : "");
    } else if (prevType === "workoutpicker") {
      if (saved === "none") { setWorkoutDays([]); setWorkoutSlot("i don't work out"); }
      else {
        const parts = saved.split(" – ");
        setWorkoutDays(parts[0] ? parts[0].split(", ") : []);
        setWorkoutSlot(parts[1] || "");
      }
    } else {
      setCurrent(saved || (prevType === "slider" ? "5" : ""));
    }
    setStep((s) => s - 1);
  }

  async function submitProfile(profile) {
    setLoading(true);
    try {
      const token = localStorage.getItem("token") || sessionStorage.getItem("token");
      if (!token) {
        router.push("/login");
        return;
      }
      
      const response = await fetch("/api/profile", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify(profile),
      });

      if (response.ok) {
        // Save to localStorage as cache (will be user-specific via profile fetch)
        localStorage.setItem("campusfuel_profile", JSON.stringify(profile));
        router.push("/ai");
      } else {
        // Get error details from response
        const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
        console.error("Profile save failed:", response.status, errorData);
        throw new Error(errorData.error || `Failed to save profile (${response.status})`);
      }
    } catch (err) {
      console.error("Profile save error:", err);
      setError("Failed to save your profile. Please try again.");
      setLoading(false);
    }
  }

  const sliderVal = q.type === "slider" ? (current || "5") : "5";

  return (
    <div className={styles.page}>
      {/* Ambient orbs */}
      <div className={`${styles.orb} ${styles.orbGreen}`} />
      <div className={`${styles.orb} ${styles.orbGold}`} />
      
      {/* Header */}
      <div className={styles.topBar}>
        <span className={styles.brand}>🌿 CampusFuel</span>
        <span className={styles.stepCount}>{step + 1} / {STEPS.length}</span>
      </div>

      {/* Pill progress bar */}
      <div className={styles.pillBar}>
        {STEPS.map((_, i) => (
          <div
            key={i}
            className={`${styles.pill} ${i < step ? styles.pillDone : ""} ${i === step ? styles.pillActive : ""}`}
          />
        ))}
      </div>

      <div className={styles.card}>
        {/* Emoji + question */}
        <div className={styles.emoji}>{q.emoji}</div>
        <h2 className={styles.question}>{q.question}</h2>

        {/* Input */}
        <div className={styles.inputWrap}>

          {q.type === "text" && (
            <input
              key={q.key}
              type="text"
              className={styles.input}
              placeholder={q.placeholder}
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleNext()}
              autoFocus
            />
          )}

          {q.type === "textarea" && (
            <textarea
              key={q.key}
              className={styles.textarea}
              placeholder={q.placeholder}
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              rows={4}
              autoFocus
            />
          )}

          {q.type === "select" && (
            <div className={styles.options}>
              {q.options.map((opt) => (
                <button
                  key={opt}
                  className={`${styles.optBtn} ${current === opt.toLowerCase() ? styles.optActive : ""}`}
                  onClick={() => setCurrent(opt.toLowerCase())}
                  type="button"
                >
                  {opt}
                </button>
              ))}
            </div>
          )}

          {q.type === "slider" && (
            <div className={styles.sliderWrap}>
              <div className={styles.sliderLabels}>
                <span>{q.labels[0]}</span>
                <span>{q.labels[1]}</span>
              </div>
              <input
                type="range"
                min={q.min}
                max={q.max}
                value={sliderVal}
                onChange={(e) => setCurrent(e.target.value)}
                className={styles.slider}
              />
              <div className={styles.sliderVal}>{sliderVal} / {q.max}</div>
            </div>
          )}

          {q.type === "daypicker" && (
            <div className={styles.pickerWrap}>
              <p className={styles.pickerHint}>{q.hint}</p>
              <div className={styles.dayRow}>
                {DAYS.map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={`${styles.dayBtn} ${selectedDays.includes(d) ? styles.dayBtnOn : ""}`}
                    onClick={() => setSelectedDays((prev) =>
                      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]
                    )}
                  >
                    {d}
                  </button>
                ))}
              </div>
              {selectedDays.length > 0 && (
                <p className={styles.pickerSummary}>📅 {selectedDays.join(" · ")}</p>
              )}
            </div>
          )}

          {q.type === "sleeppicker" && (
            <div className={styles.pickerWrap}>
              <div className={styles.sleepRow}>
                <div className={styles.sleepGroup}>
                  <span className={styles.sleepLabel}>🌙 Bedtime</span>
                  <div className={styles.timeGrid}>
                    {q.bedTimes.map((t) => (
                      <button
                        key={t}
                        type="button"
                        className={`${styles.timeBtn} ${bedTime === t ? styles.timeBtnOn : ""}`}
                        onClick={() => setBedTime(t)}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
                <div className={styles.sleepDivider} />
                <div className={styles.sleepGroup}>
                  <span className={styles.sleepLabel}>☀️ Wake up</span>
                  <div className={styles.timeGrid}>
                    {q.wakeTimes.map((t) => (
                      <button
                        key={t}
                        type="button"
                        className={`${styles.timeBtn} ${wakeTime === t ? styles.timeBtnOn : ""}`}
                        onClick={() => setWakeTime(t)}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              {bedTime && wakeTime && (
                <p className={styles.pickerSummary}>😴 Sleep {bedTime} → Wake {wakeTime}</p>
              )}
            </div>
          )}

          {q.type === "workoutpicker" && (
            <div className={styles.pickerWrap}>
              <p className={styles.sleepLabel}>📆 Which days?</p>
              <div className={styles.dayRow}>
                {DAYS.map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={`${styles.dayBtn} ${workoutDays.includes(d) ? styles.dayBtnOn : ""} ${workoutSlot === "i don't work out" ? styles.dayBtnDisabled : ""}`}
                    onClick={() => {
                      if (workoutSlot === "i don't work out") return;
                      setWorkoutDays((prev) =>
                        prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d]
                      );
                    }}
                  >
                    {d}
                  </button>
                ))}
              </div>
              <p className={styles.sleepLabel} style={{ marginTop: "18px" }}>⏰ What time?</p>
              <div className={styles.slotRow}>
                {WORKOUT_SLOTS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={`${styles.slotBtn} ${workoutSlot === s.toLowerCase() ? styles.slotBtnOn : ""}`}
                    onClick={() => {
                      const val = s.toLowerCase();
                      setWorkoutSlot(val);
                      if (val === "i don't work out") setWorkoutDays([]);
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
              {((workoutDays.length > 0 && workoutSlot && workoutSlot !== "i don't work out") || workoutSlot === "i don't work out") && (
                <p className={styles.pickerSummary}>
                  {workoutSlot === "i don't work out" ? "🛋️ No workouts" : `🏋️ ${workoutDays.join(" · ")} – ${workoutSlot}`}
                </p>
              )}
            </div>
          )}

        </div>

        {error && <p className={styles.error}>{error}</p>}

        {/* Navigation */}
        <div className={styles.nav}>
          {step > 0 && (
            <button className={styles.backBtn} onClick={handleBack} type="button">
              ← Back
            </button>
          )}
          <button
            className={styles.nextBtn}
            onClick={handleNext}
            disabled={loading}
            type="button"
          >
            {loading ? "Saving..." : isLast ? "Finish & Start AI Chat 🚀" : "Next →"}
          </button>
        </div>
      </div>

    </div>
  );
}
