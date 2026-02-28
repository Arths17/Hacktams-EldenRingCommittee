"""
HealthOS — User State Vector Engine  (v1.0)
============================================

Four interlocked architecture layers:

  Layer 1 · User State Vector
            analyze_user_state(profile)       → structured UserState dict
            map_state_to_protocols(state)      → {protocol: severity_score}
            protocols_to_nutrients(protocols)  → {nutrient: daily_target}

  Layer 2 · Protocol Prioritization Engine
            PROTOCOL_WEIGHTS                   — base learnable weights for 30 protocols
            prioritize_protocols(...)          → ranked [(protocol, score)]
            priority = severity × weight × goal_alignment

  Layer 3 · Constraint Solver
            ConstraintSet                      — 6 real-world constraint types
            build_constraints_from_profile()   → ConstraintSet
            solve_constraints(...)             → context dict

  Layer 4 · Feedback Learning Loop
            parse_feedback_from_text(text)     → {signal: delta}
            update_weights_from_feedback(...)  → updated weights (persisted)
            load/save_feedback_weights()       — per-user JSON weight files
"""

import os
import re
import json
import math
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════
# LAYER 1a — BASE PROTOCOL WEIGHT TABLE
#   Reflects general clinical importance.
#   Nudged per-user via the Feedback Learning Loop.
# ══════════════════════════════════════════════
PROTOCOL_WEIGHTS: dict[str, float] = {
    "sleep_protocol":             0.90,
    "stress_protocol":            0.85,
    "energy_protocol":            0.80,
    "mood_protocol":              0.75,
    "cognitive_protocol":         0.72,
    "gut_protocol":               0.70,
    "hydration_protocol":         0.70,
    "immune_protocol":            0.65,
    "blood_sugar_protocol":       0.65,
    "heart_protocol":             0.65,
    "anti_inflammatory_protocol": 0.65,
    "electrolyte_protocol":       0.65,
    "b_complex_protocol":         0.65,
    "omega_protocol":             0.62,
    "recovery_protocol":          0.62,
    "performance_protocol":       0.60,
    "muscle_protocol":            0.60,
    "thyroid_protocol":           0.58,
    "zinc_protocol":              0.55,
    "vitamin_c_protocol":         0.55,
    "fat_loss_protocol":          0.55,
    "antioxidant_protocol":       0.55,
    "hormone_protocol":           0.55,
    "probiotic_protocol":         0.55,
    "bone_protocol":              0.50,
    "liver_protocol":             0.50,
    "detox_protocol":             0.48,
    "vision_protocol":            0.42,
    "skin_protocol":              0.40,
    "collagen_protocol":          0.40,
}


# ══════════════════════════════════════════════
# LAYER 1b — GOAL ↔ PROTOCOL ALIGNMENT
#   How well each protocol supports each user goal (0.0–1.0).
#   DEFAULT applies to any protocol not explicitly listed.
# ══════════════════════════════════════════════
GOAL_PROTOCOL_ALIGNMENT: dict[str, dict[str, float]] = {
    "fat loss": {
        "fat_loss_protocol":          1.00,
        "blood_sugar_protocol":       0.90,
        "gut_protocol":               0.75,
        "energy_protocol":            0.80,
        "sleep_protocol":             0.85,
        "stress_protocol":            0.85,
        "anti_inflammatory_protocol": 0.70,
        "hydration_protocol":         0.80,
        "probiotic_protocol":         0.65,
        "muscle_protocol":            0.50,
        "heart_protocol":             0.65,
        "mood_protocol":              0.70,
        "cognitive_protocol":         0.65,
        "DEFAULT":                    0.50,
    },
    "muscle gain": {
        "muscle_protocol":            1.00,
        "recovery_protocol":          0.95,
        "performance_protocol":       0.90,
        "energy_protocol":            0.85,
        "sleep_protocol":             0.85,
        "b_complex_protocol":         0.75,
        "zinc_protocol":              0.80,
        "electrolyte_protocol":       0.75,
        "fat_loss_protocol":          0.35,
        "blood_sugar_protocol":       0.70,
        "stress_protocol":            0.75,
        "mood_protocol":              0.65,
        "DEFAULT":                    0.55,
    },
    "maintenance": {
        "gut_protocol":               0.80,
        "immune_protocol":            0.80,
        "heart_protocol":             0.80,
        "sleep_protocol":             0.80,
        "stress_protocol":            0.80,
        "mood_protocol":              0.75,
        "cognitive_protocol":         0.75,
        "hydration_protocol":         0.75,
        "anti_inflammatory_protocol": 0.75,
        "blood_sugar_protocol":       0.70,
        "DEFAULT":                    0.65,
    },
    "general health": {
        "immune_protocol":            0.90,
        "gut_protocol":               0.88,
        "anti_inflammatory_protocol": 0.85,
        "sleep_protocol":             0.85,
        "stress_protocol":            0.85,
        "heart_protocol":             0.82,
        "mood_protocol":              0.80,
        "cognitive_protocol":         0.80,
        "antioxidant_protocol":       0.78,
        "hydration_protocol":         0.78,
        "DEFAULT":                    0.70,
    },
}


# ══════════════════════════════════════════════
# LAYER 1c — PROTOCOL → NUTRIENT TARGETS
#   Daily intake targets (native units) driven by each protocol.
#   Keys must match NUTRIENT_THRESHOLDS in nutrition_db.py.
# ══════════════════════════════════════════════
PROTOCOL_NUTRIENT_TARGETS: dict[str, list[tuple[str, float]]] = {
    "sleep_protocol":             [("tryptophan_mg", 350),  ("magnesium_mg", 420),  ("calcium_mg", 1000)],
    "stress_protocol":            [("magnesium_mg", 420),   ("vitamin_b6_mg", 1.3), ("vitamin_c_mg", 90)],
    "energy_protocol":            [("iron_mg", 18),         ("vitamin_b12_ug", 2.4),("vitamin_b6_mg", 1.3)],
    "mood_protocol":              [("tryptophan_mg", 350),  ("vitamin_d_ug", 15),   ("vitamin_b12_ug", 2.4)],
    "cognitive_protocol":         [("choline_mg", 550),     ("vitamin_b12_ug", 2.4),("zinc_mg", 11)],
    "gut_protocol":               [("fiber_g", 38),         ("magnesium_mg", 320)],
    "immune_protocol":            [("vitamin_c_mg", 90),    ("zinc_mg", 11),        ("vitamin_d_ug", 15)],
    "blood_sugar_protocol":       [("fiber_g", 38),         ("magnesium_mg", 320),  ("vitamin_b6_mg", 1.3)],
    "muscle_protocol":            [("protein_g", 80),       ("calcium_mg", 1000),   ("zinc_mg", 11)],
    "recovery_protocol":          [("protein_g", 80),       ("magnesium_mg", 420),  ("vitamin_c_mg", 90)],
    "heart_protocol":             [("potassium_mg", 4700),  ("fiber_g", 38),        ("magnesium_mg", 420)],
    "anti_inflammatory_protocol": [("vitamin_c_mg", 90),    ("magnesium_mg", 420)],
    "electrolyte_protocol":       [("sodium_mg", 1500),     ("potassium_mg", 4700), ("magnesium_mg", 420)],
    "b_complex_protocol":         [("vitamin_b12_ug", 2.4), ("vitamin_b6_mg", 1.3), ("choline_mg", 550)],
    "bone_protocol":              [("calcium_mg", 1000),    ("vitamin_d_ug", 15),   ("magnesium_mg", 420)],
    "fat_loss_protocol":          [("protein_g", 80),       ("fiber_g", 38)],
    "hydration_protocol":         [("potassium_mg", 4700),  ("sodium_mg", 1500)],
    "zinc_protocol":              [("zinc_mg", 11)],
    "vitamin_c_protocol":         [("vitamin_c_mg", 90)],
    "omega_protocol":             [],   # tracked as food type, not isolated nutrient
    "probiotic_protocol":         [],   # tracked as food type
    "thyroid_protocol":           [("zinc_mg", 11),         ("iron_mg", 18)],
    "performance_protocol":       [("protein_g", 80),       ("iron_mg", 18)],
    "hormone_protocol":           [("zinc_mg", 11),         ("vitamin_d_ug", 15),   ("choline_mg", 550)],
    "antioxidant_protocol":       [("vitamin_c_mg", 90)],
    "liver_protocol":             [("choline_mg", 550),     ("vitamin_b6_mg", 1.3)],
    "detox_protocol":             [("fiber_g", 38),         ("vitamin_c_mg", 90)],
    "vision_protocol":            [],
    "skin_protocol":              [("vitamin_c_mg", 90),    ("zinc_mg", 11)],
    "collagen_protocol":          [("vitamin_c_mg", 90),    ("protein_g", 80)],
}


# Protocols that should not both be pushed at high priority simultaneously
PROTOCOL_CONFLICTS: list[frozenset] = [
    frozenset({"fat_loss_protocol", "muscle_protocol"}),    # surplus vs deficit
    frozenset({"detox_protocol", "muscle_protocol"}),       # low calorie vs high protein
    frozenset({"sleep_protocol", "performance_protocol"}),  # rest vs stimulate
]


# ══════════════════════════════════════════════
# LAYER 2 — USER STATE VECTOR
# ══════════════════════════════════════════════

def _parse_sleep_hours(profile: dict) -> Optional[float]:
    """Extract numeric sleep hours from the sleep_schedule profile field."""
    raw = profile.get("sleep_schedule", "")
    cleaned = raw.lower()
    cleaned = cleaned.replace("–", "-").replace("—", "-")
    cleaned = re.sub(r"\bto\b",   "-", cleaned)
    cleaned = re.sub(r"\band\b",  "-", cleaned)
    cleaned = re.sub(r"\bwake\s*(up)?\b", "-", cleaned)
    cleaned = re.sub(r"\buntil\b", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)

    time_pat = r"(\d{1,2}(?::\d{2})?)\s*(am|pm)"
    times = re.findall(time_pat, cleaned)
    if len(times) < 2:
        return None

    def _to_h(time_str: str, ampm: str) -> float:
        parts = time_str.split(":")
        h = int(parts[0])
        mins = int(parts[1]) if len(parts) > 1 else 0
        if ampm == "pm" and h != 12:
            h += 12
        if ampm == "am" and h == 12:
            h = 0
        return h + mins / 60.0

    bed  = _to_h(times[0][0], times[0][1])
    wake = _to_h(times[1][0], times[1][1])
    hours = (24 - bed + wake) if bed > wake else (wake - bed)
    if hours == 0 or hours > 23:
        return None
    return round(hours, 1)


def _infer_mental_state(profile: dict) -> list[str]:
    """Infer behavioural/mental state tags from profile numeric + text fields."""
    tags = []
    try:
        stress = int(profile.get("stress_level", 5))
        energy = int(profile.get("energy_level", 5))
    except (ValueError, TypeError):
        stress, energy = 5, 5

    mood          = profile.get("mood", "neutral").lower()
    sleep_quality = profile.get("sleep_quality", "okay").lower()
    extra         = profile.get("extra", "").lower()

    if stress >= 8:
        tags.append("high_stress")
    if stress >= 9:
        tags.append("burnout_risk")
    if energy <= 3:
        tags.append("energy_crisis")
    if mood == "low":
        tags.append("low_mood")
    if sleep_quality == "poor":
        tags.append("sleep_deprived")
    if any(w in extra for w in ("anxiety", "anxious", "panic", "worried")):
        tags.append("anxiety")
    if any(w in extra for w in ("depress", "sad", "hopeless", "unmotivated")):
        tags.append("depression_risk")
    if any(w in extra for w in ("focus", "concentrate", "brain fog", "distract")):
        tags.append("low_focus")
    if energy <= 4 and mood == "low":
        tags.append("fatigue")
    if energy <= 2 and stress >= 8:
        tags.append("crash_risk")
    return tags


def _infer_activity_level(profile: dict) -> str:
    workout = profile.get("workout_times", "none").lower()
    if "none" in workout or not workout.strip():
        return "sedentary"
    if any(w in workout for w in ["every day", "daily", "twice"]):
        return "active"
    if any(w in workout for w in ["3", "4", "5", "three", "four", "five"]):
        return "moderate"
    return "light"


_GOAL_NORM: dict[str, str] = {
    "fat loss": "fat loss",         "weight loss": "fat loss",
    "lose weight": "fat loss",      "cut": "fat loss",
    "muscle gain": "muscle gain",   "bulk": "muscle gain",
    "gain muscle": "muscle gain",   "build muscle": "muscle gain",
    "maintenance": "maintenance",   "maintain": "maintenance",
    "general health": "general health",
    "health": "general health",     "wellness": "general health",
}


def analyze_user_state(profile: dict) -> dict:
    """
    Build a structured UserState from the raw profile dict.

    Returns
    -------
    dict with keys:
        sleep_hours      : float | None
        stress_level     : int
        energy_level     : int
        activity_level   : "sedentary" | "light" | "moderate" | "active"
        mental_state     : [str]  — inferred behavioural tags
        goals            : [str]  — normalised goal strings
        schedule         : {sleep_window, class_blocks, gym_time}
        constraints_raw  : {budget, cooking_access, diet_type, allergies}
        computed_flags   : [str]  — critical computed warnings
    """
    try:
        stress = int(profile.get("stress_level", 5))
    except (ValueError, TypeError):
        stress = 5
    try:
        energy = int(profile.get("energy_level", 5))
    except (ValueError, TypeError):
        energy = 5

    sleep_hours  = _parse_sleep_hours(profile)
    goals_raw    = profile.get("goal", "general health").lower()
    goals        = [_GOAL_NORM.get(goals_raw, goals_raw)]
    mental_state = _infer_mental_state(profile)
    activity     = _infer_activity_level(profile)

    flags = []
    if sleep_hours is not None and sleep_hours < 5:
        flags.append(f"SEVERE_SLEEP_DEFICIT: {sleep_hours}h (threshold 5h)")
    if stress >= 9:
        flags.append("BURNOUT_IMMINENT")
    if energy <= 2 and stress >= 8:
        flags.append("CRASH_RISK: combined critical energy + critical stress")
    if "anxiety" in mental_state and "energy_crisis" in mental_state:
        flags.append("ANXIOUS_AND_DEPLETED: combined anxiety + energy crisis")

    return {
        "sleep_hours":     sleep_hours,
        "stress_level":    stress,
        "energy_level":    energy,
        "activity_level":  activity,
        "mental_state":    mental_state,
        "goals":           goals,
        "schedule": {
            "sleep_window": profile.get("sleep_schedule", ""),
            "class_blocks": profile.get("class_schedule", ""),
            "gym_time":     profile.get("workout_times", "none"),
        },
        "constraints_raw": {
            "budget":         profile.get("budget", "medium"),
            "cooking_access": profile.get("cooking_access", "shared kitchen"),
            "diet_type":      profile.get("diet_type", "omnivore"),
            "allergies":      profile.get("allergies", "none"),
        },
        "computed_flags": flags,
    }


# ══════════════════════════════════════════════
# LAYER 3 — PROTOCOL MAPPING
#   State fields + mental tags → {protocol: severity_score}
# ══════════════════════════════════════════════

_MENTAL_STATE_PROTOCOLS: dict[str, list[tuple[str, float]]] = {
    "high_stress":     [("stress_protocol", 0.85), ("gut_protocol", 0.60), ("b_complex_protocol", 0.70)],
    "burnout_risk":    [("stress_protocol", 1.00), ("sleep_protocol", 0.90), ("gut_protocol", 0.70)],
    "energy_crisis":   [("energy_protocol", 0.90), ("b_complex_protocol", 0.75), ("electrolyte_protocol", 0.65)],
    "low_mood":        [("mood_protocol", 0.80),   ("omega_protocol", 0.60),     ("gut_protocol", 0.55)],
    "sleep_deprived":  [("sleep_protocol", 0.85),  ("energy_protocol", 0.65)],
    "anxiety":         [("stress_protocol", 0.90), ("blood_sugar_protocol", 0.75), ("gut_protocol", 0.65)],
    "depression_risk": [("mood_protocol", 0.90),   ("omega_protocol", 0.70),     ("vitamin_c_protocol", 0.55)],
    "low_focus":       [("cognitive_protocol", 0.80), ("blood_sugar_protocol", 0.70), ("omega_protocol", 0.65)],
    "fatigue":         [("energy_protocol", 0.85), ("b_complex_protocol", 0.70)],
    "crash_risk":      [("sleep_protocol", 1.00),  ("energy_protocol", 1.00),    ("stress_protocol", 0.90)],
}

_GOAL_PROTOCOLS: dict[str, list[tuple[str, float]]] = {
    "fat loss":      [("fat_loss_protocol", 0.80),  ("blood_sugar_protocol", 0.70), ("gut_protocol", 0.60)],
    "muscle gain":   [("muscle_protocol", 0.80),    ("recovery_protocol", 0.75),    ("performance_protocol", 0.65)],
    "maintenance":   [("gut_protocol", 0.65),        ("immune_protocol", 0.65),      ("heart_protocol", 0.60)],
    "general health":[("immune_protocol", 0.70),    ("gut_protocol", 0.70),         ("anti_inflammatory_protocol", 0.65)],
}

_DIET_PROTOCOLS: dict[str, list[tuple[str, float]]] = {
    "vegan":       [("b_complex_protocol", 0.85), ("energy_protocol", 0.75), ("zinc_protocol", 0.70), ("bone_protocol", 0.65)],
    "vegetarian":  [("b_complex_protocol", 0.70), ("energy_protocol", 0.65)],
    "halal":       [],
    "omnivore":    [],
}


def map_state_to_protocols(state: dict) -> dict[str, float]:
    """
    Map UserState → {protocol_name: severity_score (0.0–1.0)}.

    Severity expresses urgency for this protocol given the user's
    current state. Multiple sources contribute — we take the max
    to avoid score inflation.
    """
    raw: dict[str, list[float]] = {}

    def _add(proto: str, score: float) -> None:
        raw.setdefault(proto, []).append(score)

    # ── Sleep-derived severity ──────────────────
    sleep_h = state.get("sleep_hours")
    if sleep_h is not None:
        if sleep_h < 4:    _add("sleep_protocol", 1.00)
        elif sleep_h < 5:  _add("sleep_protocol", 0.90)
        elif sleep_h < 6:  _add("sleep_protocol", 0.75)
        elif sleep_h < 7:  _add("sleep_protocol", 0.55)

    # ── Stress-derived severity ─────────────────
    stress = state.get("stress_level", 5)
    if stress >= 9:
        _add("stress_protocol", 1.00); _add("gut_protocol", 0.70)
    elif stress >= 7:
        _add("stress_protocol", 0.80); _add("gut_protocol", 0.55)
    elif stress >= 5:
        _add("stress_protocol", 0.50)

    # ── Energy-derived severity ─────────────────
    energy = state.get("energy_level", 5)
    if energy <= 2:
        _add("energy_protocol", 1.00); _add("b_complex_protocol", 0.75)
    elif energy <= 4:
        _add("energy_protocol", 0.75); _add("b_complex_protocol", 0.55)
    elif energy <= 6:
        _add("energy_protocol", 0.40)

    # ── Mental state tags ───────────────────────
    for tag in state.get("mental_state", []):
        for proto, sev in _MENTAL_STATE_PROTOCOLS.get(tag, []):
            _add(proto, sev)

    # ── Goal-derived protocols ──────────────────
    for goal in state.get("goals", ["general health"]):
        for proto, sev in _GOAL_PROTOCOLS.get(goal, _GOAL_PROTOCOLS["general health"]):
            _add(proto, sev)

    # ── Diet-derived protocols ──────────────────
    diet = state.get("constraints_raw", {}).get("diet_type", "omnivore").lower()
    for proto, sev in _DIET_PROTOCOLS.get(diet, []):
        _add(proto, sev)

    return {p: round(max(scores), 2) for p, scores in raw.items()}


def protocols_to_nutrients(active_protocols: dict[str, float]) -> dict[str, float]:
    """
    Map active protocols → {nutrient_key: daily_target}.
    When multiple protocols target the same nutrient, the max target wins.
    Targets are scaled by severity so higher-urgency protocols dominate.
    """
    targets: dict[str, float] = {}
    for proto, severity in active_protocols.items():
        for nutrient, base_target in PROTOCOL_NUTRIENT_TARGETS.get(proto, []):
            scaled = round(base_target * max(0.5, severity), 1)
            targets[nutrient] = max(targets.get(nutrient, 0), scaled)
    return targets


# ══════════════════════════════════════════════
# LAYER 4 — PROTOCOL PRIORITIZATION ENGINE
# ══════════════════════════════════════════════

def _goal_alignment(protocol: str, goals: list[str]) -> float:
    """Return the highest alignment score for a protocol across all user goals."""
    if not goals:
        return 0.65
    scores = []
    for goal in goals:
        goal_map = GOAL_PROTOCOL_ALIGNMENT.get(goal, {})
        scores.append(goal_map.get(protocol, goal_map.get("DEFAULT", 0.50)))
    return max(scores)


def _is_conflicting(proto_a: str, proto_b: str) -> bool:
    for pair in PROTOCOL_CONFLICTS:
        if proto_a in pair and proto_b in pair:
            return True
    return False


def compute_priority(
    protocol: str,
    severity: float,
    weight: float,
    goal_alignment: float,
) -> float:
    """
    priority = severity × weight × goal_alignment

    Range: 0.0 → ~1.0  (slightly above 1.0 for critical + perfectly aligned)
    """
    return round(severity * weight * goal_alignment, 4)


def prioritize_protocols(
    active_protocols: dict[str, float],
    state: dict,
    learned_weights: Optional[dict] = None,
) -> list[tuple[str, float]]:
    """
    Score and rank all active protocols.

    Steps
    -----
    1. Blend base PROTOCOL_WEIGHTS with per-user learned weights (70/30 split).
    2. Compute priority = severity × blended_weight × goal_alignment.
    3. Sort descending.
    4. Penalise lower-ranked protocols that conflict with higher-ranked ones.

    Returns
    -------
    List of (protocol_name, priority_score) sorted highest → lowest.
    """
    goals   = state.get("goals", ["general health"])
    weights = dict(PROTOCOL_WEIGHTS)

    if learned_weights:
        for proto, w in learned_weights.items():
            if proto in weights:
                # Blend: 70% base + 30% learned to prevent runaway drift
                weights[proto] = round(0.70 * weights[proto] + 0.30 * w, 4)

    scored: list[tuple[str, float]] = []
    for proto, severity in active_protocols.items():
        w         = weights.get(proto, 0.50)
        alignment = _goal_alignment(proto, goals)
        score     = compute_priority(proto, severity, w, alignment)
        scored.append((proto, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    # Conflict suppression: penalise lower-ranked conflicting protocols
    penalised: set[str] = set()
    result:    list[tuple[str, float]] = []
    for proto, score in scored:
        if proto in penalised:
            score = round(score * 0.60, 4)
        result.append((proto, score))
        # Mark all lower-ranked conflicts of this protocol
        for other, _ in scored:
            if other != proto and _is_conflicting(proto, other):
                penalised.add(other)

    return result


# ══════════════════════════════════════════════
# LAYER 5 — CONSTRAINT SOLVER
# ══════════════════════════════════════════════

@dataclass
class ConstraintSet:
    """Real-world bounds on what recommendations are actually actionable."""
    time_minutes:         int   = 30        # cooking / prep time available
    budget_daily:         float = 15.0      # $ per day
    kitchen_level:        str   = "shared"  # none | microwave | dorm microwave | shared | full
    dietary_restrictions: list  = field(default_factory=list)
    allergies:            list  = field(default_factory=list)
    mental_energy:        int   = 5         # 1–10  (low = decision fatigue)
    schedule_gaps:        list  = field(default_factory=list)


_KITCHEN_TIERS: dict[str, int] = {
    "none": 0,
    "microwave": 1, "dorm microwave": 1,
    "shared": 2,    "shared kitchen": 2,
    "full": 3,      "full kitchen": 3,
}

_BUDGET_MAP: dict[str, float] = {
    "low": 8.0, "medium": 15.0, "flexible": 30.0,
}


def build_constraints_from_profile(profile: dict) -> ConstraintSet:
    """Parse raw profile fields into a typed ConstraintSet."""
    budget_str = profile.get("budget", "medium").lower()
    budget_val = _BUDGET_MAP.get(budget_str, 15.0)

    cooking = profile.get("cooking_access", "shared kitchen").lower()

    diet_type    = profile.get("diet_type", "omnivore").lower()
    restrictions = [diet_type] if diet_type in ("vegan", "vegetarian", "halal", "kosher") else []

    allergies_raw = profile.get("allergies", "none")
    allergies = (
        []
        if allergies_raw.lower() in ("none", "no", "n/a", "")
        else [a.strip().lower() for a in re.split(r"[,;/]", allergies_raw) if a.strip()]
    )

    # Time heuristic: early wakers + morning classes → tighter prep window
    sleep_raw = profile.get("sleep_schedule", "").lower()
    time_mins = 30
    if re.search(r"\b[67]am\b", sleep_raw):      # wakes 6–7am
        time_mins = 15
    class_sch = profile.get("class_schedule", "").lower()
    if re.search(r"\b[89]am\b", class_sch):       # early class
        time_mins = max(10, time_mins - 10)

    try:
        energy = int(profile.get("energy_level", 5))
    except (ValueError, TypeError):
        energy = 5
    try:
        stress = int(profile.get("stress_level", 5))
    except (ValueError, TypeError):
        stress = 5

    # Mental energy = inverse of cognitive load
    mental_energy = max(1, min(10, 10 - max(0, stress - 5) - max(0, 5 - energy)))

    return ConstraintSet(
        time_minutes         = time_mins,
        budget_daily         = budget_val,
        kitchen_level        = cooking,
        dietary_restrictions = restrictions,
        allergies            = allergies,
        mental_energy        = mental_energy,
    )


def solve_constraints(
    prioritized_protocols: list[tuple[str, float]],
    constraints: ConstraintSet,
    state: dict,
) -> dict:
    """
    Filter + annotate protocols through real-world constraints.

    Constraint checks
    -----------------
    time          → caps protocol list if prep is urgent
    budget        → annotated in summary (food selection handled by AI)
    kitchen       → drops protocols requiring cooking when no kitchen
    dietary       → drops incompatible protocols (e.g. vegan + collagen)
    mental_energy → caps total number of active protocols

    Returns
    -------
    {
        feasible_protocols : [(proto, score)]
        skipped_protocols  : [(proto, reason)]
        constraint_summary : str  — formatted block for Gemini injection
        time_tier          : str
        budget_tier        : str
        max_protocols      : int
    }
    """
    feasible: list[tuple[str, float]] = []
    skipped:  list[tuple[str, str]]   = []

    kitchen_tier = _KITCHEN_TIERS.get(constraints.kitchen_level, 2)
    time         = constraints.time_minutes
    budget       = constraints.budget_daily
    mental_e     = constraints.mental_energy

    # Tier labels
    if time <= 10:    time_tier = "urgent"
    elif time <= 20:  time_tier = "tight"
    elif time <= 40:  time_tier = "moderate"
    else:             time_tier = "comfortable"

    if budget <= 8:    budget_tier = "bare"
    elif budget <= 12: budget_tier = "tight"
    elif budget <= 20: budget_tier = "moderate"
    else:              budget_tier = "flexible"

    # Mental energy → cap total protocol count to reduce decision fatigue
    max_protocols = 10 if mental_e >= 7 else (7 if mental_e >= 4 else 4)

    # Protocols that require cooking equipment
    _NEEDS_COOKING = {"recovery_protocol", "muscle_protocol", "performance_protocol"}

    # Protocols incompatible with vegan diet
    _VEGAN_INCOMPATIBLE = {"collagen_protocol"}

    for i, (proto, score) in enumerate(prioritized_protocols):
        if i >= max_protocols:
            skipped.append((proto, f"mental energy cap ({mental_e}/10 → max {max_protocols})"))
            continue

        if "vegan" in constraints.dietary_restrictions and proto in _VEGAN_INCOMPATIBLE:
            skipped.append((proto, "dietary restriction: vegan"))
            continue

        if kitchen_tier == 0 and proto in _NEEDS_COOKING:
            skipped.append((proto, "no kitchen — requires cooking equipment"))
            continue

        feasible.append((proto, score))

    # Build constraint summary string
    lines = [
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  ACTIVE CONSTRAINTS:",
        f"    ⏱  Time available:   {time}min  [{time_tier}]",
        f"    💰  Daily budget:     ${budget:.0f}/day  [{budget_tier}]",
        f"    🍳  Kitchen level:    {constraints.kitchen_level}",
        f"    🧠  Mental energy:    {mental_e}/10",
    ]
    if constraints.dietary_restrictions:
        lines.append(f"    🥗  Restrictions:     {', '.join(constraints.dietary_restrictions)}")
    if constraints.allergies:
        lines.append(f"    ⚠️   Allergies:         {', '.join(constraints.allergies)}")
    if skipped:
        lines.append(f"    ⏭️   Skipped protocols: {len(skipped)} (constraint conflicts)")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return {
        "feasible_protocols": feasible,
        "skipped_protocols":  skipped,
        "constraint_summary": "\n".join(lines),
        "time_tier":          time_tier,
        "budget_tier":        budget_tier,
        "max_protocols":      max_protocols,
    }


# ══════════════════════════════════════════════
# LAYER 6 — FEEDBACK LEARNING LOOP
# ══════════════════════════════════════════════

FEEDBACK_WEIGHTS_DIR: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "feedback_weights"
)

# Natural-language signal → affected protocols
FEEDBACK_PROTOCOL_MAP: dict[str, list[str]] = {
    "energy":   ["energy_protocol",  "b_complex_protocol", "electrolyte_protocol"],
    "focus":    ["cognitive_protocol","omega_protocol",     "blood_sugar_protocol"],
    "sleep":    ["sleep_protocol"],
    "stress":   ["stress_protocol",  "gut_protocol",       "anti_inflammatory_protocol"],
    "mood":     ["mood_protocol",    "omega_protocol",     "gut_protocol"],
    "gut":      ["gut_protocol",     "probiotic_protocol"],
    "muscle":   ["muscle_protocol",  "recovery_protocol",  "performance_protocol"],
    "immune":   ["immune_protocol",  "vitamin_c_protocol", "zinc_protocol"],
    "anxiety":  ["stress_protocol",  "blood_sugar_protocol","gut_protocol"],
    "hunger":   ["fat_loss_protocol","blood_sugar_protocol"],
    "bloat":    ["gut_protocol",     "probiotic_protocol"],
    "headache": ["hydration_protocol","electrolyte_protocol"],
    "cramp":    ["electrolyte_protocol","b_complex_protocol"],
}

# Regex patterns for feedback extraction
_EXPLICIT_PATTERN   = re.compile(
    r"\b(energy|focus|sleep|stress|mood|gut|muscle|immune|anxiety|hunger|bloat|headache|cramp)"
    r"\s*[:\-]?\s*([+-]?\d+(?:\.\d+)?)"
)
_IMPROVED_PATTERN   = re.compile(
    r"\b(?:my\s+)?(energy|focus|sleep|mood|gut|stress)\s+(?:is\s+)?(improved|better|great|good|up)\b"
)
_WORSENED_PATTERN   = re.compile(
    r"\b(?:my\s+)?(energy|focus|sleep|mood|gut|stress)\s+(?:is\s+)?(worse|bad|terrible|down|lower)\b"
)
_POS_ADJ_PATTERN    = re.compile(r"\b(?:more|better)\s+(energetic|focused|rested|calm|happy)\b")
_NEG_ADJ_PATTERN    = re.compile(r"\b(?:less|worse|more)\s+(tired|stressed|anxious|bloated)\b")

_ADJ_SIGNAL: dict[str, str] = {
    "energetic": "energy", "focused": "focus", "rested": "sleep",
    "calm":      "stress", "happy":   "mood",
    "tired":     "energy", "stressed":"stress", "anxious": "anxiety", "bloated": "bloat",
}


def parse_feedback_from_text(text: str) -> dict[str, float]:
    """
    Extract feedback signals from natural-language user input.

    Examples
    --------
    "energy +2, focus +1, sleep -1"  → {"energy": 2.0, "focus": 1.0, "sleep": -1.0}
    "I feel more energetic today"    → {"energy": 1.0}
    "my stress is worse"             → {"stress": -1.0}
    """
    signals: dict[str, float] = {}
    tl = text.lower()

    # Pattern 1: explicit  "energy: +2"
    for m in _EXPLICIT_PATTERN.finditer(tl):
        try:
            signals[m.group(1)] = float(m.group(2))
        except ValueError:
            pass

    # Pattern 2: "X improved / better"
    for m in _IMPROVED_PATTERN.finditer(tl):
        key = m.group(1)
        if key not in signals:
            signals[key] = 1.0

    # Pattern 3: "X worse / bad"
    for m in _WORSENED_PATTERN.finditer(tl):
        key = m.group(1)
        if key not in signals:
            signals[key] = -1.0

    # Pattern 4: "more/better energetic / focused / ..."
    for m in _POS_ADJ_PATTERN.finditer(tl):
        key = _ADJ_SIGNAL.get(m.group(1))
        if key and key not in signals:
            signals[key] = 1.0

    # Pattern 5: "more tired / stressed / ..."
    for m in _NEG_ADJ_PATTERN.finditer(tl):
        key = _ADJ_SIGNAL.get(m.group(1))
        if key and key not in signals:
            signals[key] = -1.0

    return signals


def load_feedback_weights(user_name: str) -> dict[str, float]:
    """Load per-user learned protocol weights; returns base table if no file yet."""
    os.makedirs(FEEDBACK_WEIGHTS_DIR, exist_ok=True)
    safe = re.sub(r"[^\w\-]", "_", user_name.lower())
    path = os.path.join(FEEDBACK_WEIGHTS_DIR, f"weights_{safe}.json")
    if os.path.exists(path):
        try:
            with open(path, "r") as fh:
                return json.load(fh)
        except Exception:
            pass
    return dict(PROTOCOL_WEIGHTS)


def save_feedback_weights(user_name: str, weights: dict[str, float]) -> None:
    """Persist per-user learned weights to disk."""
    os.makedirs(FEEDBACK_WEIGHTS_DIR, exist_ok=True)
    safe = re.sub(r"[^\w\-]", "_", user_name.lower())
    path = os.path.join(FEEDBACK_WEIGHTS_DIR, f"weights_{safe}.json")
    with open(path, "w") as fh:
        json.dump(weights, fh, indent=2)


def update_weights_from_feedback(
    user_name: str,
    feedback: dict[str, float],
    learning_rate: float = 0.05,
) -> dict[str, float]:
    """
    Bayesian-style weight update driven by user-reported outcomes.

    Algorithm
    ---------
    For each signal in feedback:
      • Positive delta (improved) → modest boost (was working, keep it)
      • Negative delta (worsened) → stronger boost (needs more attention)

    For each affected protocol:
      w_new = clip(w_old + lr_adjusted, min=0.10, max=1.00)

    Parameters
    ----------
    user_name     : used to load / save the per-user weight file
    feedback      : {signal: delta}  e.g. {"energy": +2, "sleep": -1}
    learning_rate : step size per unit of feedback (default 0.05)

    Returns
    -------
    Updated weights dict (also persisted to disk).
    """
    weights = load_feedback_weights(user_name)

    for signal, delta in feedback.items():
        # Positive outcome → small boost; negative → larger boost
        lr_adj = learning_rate * 0.5 if delta > 0 else learning_rate * abs(delta)
        for proto in FEEDBACK_PROTOCOL_MAP.get(signal, []):
            if proto in weights:
                weights[proto] = round(max(0.10, min(1.00, weights[proto] + lr_adj)), 4)

    save_feedback_weights(user_name, weights)
    return weights


# ══════════════════════════════════════════════
# LAYER 7 — CONTEXT BLOCK FORMATTER
#   Builds the block injected into the Gemini seed message.
# ══════════════════════════════════════════════

def format_priority_block(
    prioritized:       list[tuple[str, float]],
    nutrient_targets:  dict[str, float],
    constraint_result: dict,
) -> str:
    """
    Format the combined priority + constraint + nutrient-target block
    for injection into the Gemini seed message.
    """
    lines = [
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  PROTOCOL PRIORITY SCORES:",
    ]

    for i, (proto, score) in enumerate(prioritized[:10], 1):
        if score >= 0.60:   tier = "🔴 HIGH"
        elif score >= 0.40: tier = "🟠 MODERATE"
        else:               tier = "🟡 LOW"
        lines.append(f"    {i:2d}. {proto:<34} {score:.3f}  {tier}")

    skipped = constraint_result.get("skipped_protocols", [])
    if skipped:
        lines.append(f"\n  ⏭️  CONSTRAINT-FILTERED ({len(skipped)} protocols):")
        for proto, reason in skipped[:4]:
            lines.append(f"    • {proto}: {reason}")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("  DAILY NUTRIENT TARGETS (from active protocols):")
    for nutrient, target in sorted(nutrient_targets.items()):
        unit = (
            "µg" if nutrient.endswith("_ug") else
            "mg" if nutrient.endswith("_mg") else
            "g"  if nutrient.endswith("_g")  else ""
        )
        lines.append(f"    • {nutrient.replace('_', ' '):<24} → {target:.1f}{unit}")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(constraint_result.get("constraint_summary", ""))

    return "\n".join(lines)
