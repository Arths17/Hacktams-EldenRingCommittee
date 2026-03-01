"""
HealthOS — Input Validation & Semantic Parsing Pipeline  (model/validation.py)
===============================================================================
Replaces the current pattern of:
    User Input → AI Reasoning Engine  (garbage in, chaos out)

With:
    User Input
    → Stage 1: Sanitize       (strip, coerce, cap length)
    → Stage 2: Normalize      (alias expansion, typo correction, unit unification)
    → Stage 3: Semantic Parse (extract typed entities from freetext)
    → Stage 4: Ontology Map   (strings → enums → ParsedProfile)
    → AI Reasoning Engine

Usage:
    from validation import parse_profile
    pp = parse_profile(raw_dict)   # → ParsedProfile
"""
from __future__ import annotations

import re
from typing import Optional

from ontology import (
    ParsedProfile,
    DietType, AllergenType, GoalType,
    StressState, EnergyState, SleepQuality, MoodState,
    BudgetTier, KitchenAccess,
)


# ══════════════════════════════════════════════
# ALIAS TABLES  (Stage 2)
# ══════════════════════════════════════════════

_DIET_ALIASES: dict[str, DietType] = {
    # vegetarian (+ common typos)
    "vegetarian": DietType.VEGETARIAN, "vegitarian":  DietType.VEGETARIAN,
    "vegetrain":  DietType.VEGETARIAN, "vegatarian":  DietType.VEGETARIAN,
    "vegiterian": DietType.VEGETARIAN, "veg":         DietType.VEGETARIAN,
    "veggie":     DietType.VEGETARIAN,
    # vegan
    "vegan":       DietType.VEGAN, "plant based":  DietType.VEGAN,
    "plant-based": DietType.VEGAN, "plantbased":   DietType.VEGAN,
    # omnivore
    "omnivore":   DietType.OMNIVORE, "omni":       DietType.OMNIVORE,
    "everything": DietType.OMNIVORE, "non veg":    DietType.OMNIVORE,
    "non-veg":    DietType.OMNIVORE, "meat eater": DietType.OMNIVORE,
    # halal / kosher
    "halal":  DietType.HALAL,  "kosher": DietType.KOSHER,
    # pescatarian
    "pescatarian": DietType.PESCATARIAN, "pescetarian": DietType.PESCATARIAN,
    "pescitarian": DietType.PESCATARIAN,
    # other
    "keto":        DietType.KETO,
    "paleo":       DietType.PALEO,
    "gluten free": DietType.GLUTEN_FREE, "gluten-free": DietType.GLUTEN_FREE,
    "gf":          DietType.GLUTEN_FREE,
}

_GOAL_ALIASES: dict[str, GoalType] = {
    "fat loss":       GoalType.FAT_LOSS,    "lose weight":  GoalType.FAT_LOSS,
    "lose fat":       GoalType.FAT_LOSS,    "cut":          GoalType.FAT_LOSS,
    "cutting":        GoalType.FAT_LOSS,    "slim down":    GoalType.FAT_LOSS,
    "weight loss":    GoalType.FAT_LOSS,
    "muscle gain":    GoalType.MUSCLE_GAIN, "bulk":         GoalType.MUSCLE_GAIN,
    "gain muscle":    GoalType.MUSCLE_GAIN, "build muscle": GoalType.MUSCLE_GAIN,
    "bulking":        GoalType.MUSCLE_GAIN, "gain weight":  GoalType.MUSCLE_GAIN,
    "maintenance":    GoalType.MAINTENANCE, "maintain":     GoalType.MAINTENANCE,
    "stay same":      GoalType.MAINTENANCE, "maintain weight": GoalType.MAINTENANCE,
    "general health": GoalType.GENERAL_HEALTH, "health":    GoalType.GENERAL_HEALTH,
    "healthy":        GoalType.GENERAL_HEALTH, "wellness":  GoalType.GENERAL_HEALTH,
    "stay healthy":   GoalType.GENERAL_HEALTH,
}

_MOOD_ALIASES: dict[str, MoodState] = {
    "low":      MoodState.LOW,     "bad":      MoodState.LOW,
    "sad":      MoodState.LOW,     "depressed":MoodState.LOW,
    "down":     MoodState.LOW,     "rough":    MoodState.LOW,
    "terrible": MoodState.LOW,     "awful":    MoodState.LOW,
    "ok":       MoodState.NEUTRAL, "okay":     MoodState.NEUTRAL,
    "fine":     MoodState.NEUTRAL, "meh":      MoodState.NEUTRAL,
    "alright":  MoodState.NEUTRAL, "average":  MoodState.NEUTRAL,
    "neutral":  MoodState.NEUTRAL, "so-so":    MoodState.NEUTRAL,
    "good":     MoodState.GOOD,    "great":    MoodState.GOOD,
    "amazing":  MoodState.GOOD,    "awesome":  MoodState.GOOD,
    "happy":    MoodState.GOOD,    "excellent":MoodState.GOOD,
    "positive": MoodState.GOOD,
}

_SLEEP_QUALITY_ALIASES: dict[str, SleepQuality] = {
    "terrible": SleepQuality.POOR, "bad":     SleepQuality.POOR,
    "awful":    SleepQuality.POOR, "rough":   SleepQuality.POOR,
    "horrible": SleepQuality.POOR, "poor":    SleepQuality.POOR,
    "not good": SleepQuality.POOR,
    "ok":       SleepQuality.OKAY, "okay":    SleepQuality.OKAY,
    "fine":     SleepQuality.OKAY, "alright": SleepQuality.OKAY,
    "decent":   SleepQuality.OKAY, "average": SleepQuality.OKAY,
    "good":     SleepQuality.GOOD, "great":   SleepQuality.GOOD,
    "amazing":  SleepQuality.GOOD, "well":    SleepQuality.GOOD,
    "excellent":SleepQuality.GOOD,
}

_BUDGET_ALIASES: dict[str, BudgetTier] = {
    "low":      BudgetTier.LOW,
    "medium":   BudgetTier.MEDIUM, "mid":        BudgetTier.MEDIUM,
    "moderate": BudgetTier.MEDIUM,
    "flexible": BudgetTier.FLEXIBLE, "high":     BudgetTier.FLEXIBLE,
    "no limit": BudgetTier.FLEXIBLE, "unlimited":BudgetTier.FLEXIBLE,
}

_KITCHEN_ALIASES: list[tuple[str, KitchenAccess]] = [
    # Ordered longest-match first so "full kitchen" matches before "kitchen"
    ("full kitchen",   KitchenAccess.FULL_KITCHEN),
    ("shared kitchen", KitchenAccess.SHARED_KITCHEN),
    ("shared",         KitchenAccess.SHARED_KITCHEN),
    ("dorm microwave", KitchenAccess.MICROWAVE_ONLY),
    ("microwave only", KitchenAccess.MICROWAVE_ONLY),
    ("microwave",      KitchenAccess.MICROWAVE_ONLY),
    ("no kitchen",     KitchenAccess.NONE),
    ("none",           KitchenAccess.NONE),
]


# ══════════════════════════════════════════════
# ALLERGEN SEMANTIC KEYWORD MAP  (Stage 3)
# Each AllergenType maps to the keywords that trigger it in freetext.
# ══════════════════════════════════════════════
_ALLERGEN_KEYWORDS: dict[AllergenType, list[str]] = {
    AllergenType.GLUTEN:    ["gluten", "celiac", "coeliac"],
    AllergenType.DAIRY:     ["dairy", "milk", "cheese", "butter", "cream", "whey"],
    AllergenType.EGGS:      ["egg", "eggs"],
    AllergenType.PEANUTS:   ["peanut", "peanuts", "groundnut"],
    AllergenType.TREE_NUTS: ["tree nut", "tree nuts", "nut allergy",
                              "almond", "walnut", "cashew", "pecan",
                              "pistachio", "hazelnut", "macadamia"],
    AllergenType.SOY:       ["soy", "soya", "soybean", "tofu"],
    AllergenType.FISH:      ["fish", "salmon", "tuna", "cod", "tilapia",
                              "halibut", "sardine"],
    AllergenType.SHELLFISH: ["shellfish", "shrimp", "prawn", "crab",
                              "lobster", "clam", "oyster", "scallop", "mussel"],
    AllergenType.WHEAT:     ["wheat"],
    AllergenType.SESAME:    ["sesame", "tahini"],
    AllergenType.LEGUMES:   ["legume", "legumes", "lentil",
                              "chickpea", "bean", "beans"],
    AllergenType.LACTOSE:   ["lactose"],
    AllergenType.FRUCTOSE:  ["fructose"],
    AllergenType.SULFITES:  ["sulfite", "sulphite", "sulfites", "sulphites",
                              "wine allergy"],
}

# Phrases that indicate no allergies
_NO_ALLERGY_PHRASES = {
    "none", "no", "n/a", "na", "nope", "nothing", "nil",
    "no allergies", "no allergy", "no food allergies",
    "no known allergies", "i don't have any", "i have no",
}


# ══════════════════════════════════════════════
# STAGE 1 — SANITIZE
# ══════════════════════════════════════════════
def _sanitize(raw: dict) -> dict:
    """Strip whitespace, coerce None/int/float to str, cap length at 500 chars."""
    out: dict = {}
    for k, v in raw.items():
        if v is None:
            out[k] = ""
        elif isinstance(v, (int, float)):
            out[k] = str(v)
        elif isinstance(v, str):
            out[k] = v.strip()[:500]
        else:
            out[k] = str(v).strip()[:500]
    return out


# ══════════════════════════════════════════════
# STAGE 2 — NORMALIZE
# ══════════════════════════════════════════════
def _parse_scale(raw: str) -> Optional[int]:
    """Extract and clamp a 1–10 integer from a raw string."""
    m = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not m:
        return None
    try:
        return max(1, min(10, round(float(m.group(1)))))
    except ValueError:
        return None


def _parse_sleep_hours(raw: str) -> Optional[float]:
    """
    Extract sleep duration in hours from a schedule string.
    Handles: '2am-8am', '11pm–7am', '2am to 8am', 'sleep 2am wake 8am'.
    """
    if not raw:
        return None
    text = raw.lower()
    text = re.sub(r"[–—]", "-", text)
    text = re.sub(r"\b(to|and|until|wake\s*(?:up)?)\b", "-", text)
    text = re.sub(r"-+", "-", text)

    time_pat = r"(\d{1,2}(?::\d{2})?)\s*(am|pm)"
    times = re.findall(time_pat, text)
    if len(times) < 2:
        return None

    def to_h(t: str, ap: str) -> float:
        parts = t.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        if ap == "pm" and h != 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        return h + m / 60.0

    bed  = to_h(*times[0])
    wake = to_h(*times[1])
    hours = (24 - bed + wake) if bed > wake else (wake - bed)
    return round(hours, 1) if 0 < hours <= 23 else None


# ══════════════════════════════════════════════
# STAGE 3 — SEMANTIC PARSING
# Extract typed entities from freetext fields
# ══════════════════════════════════════════════
def _parse_allergens(raw: str) -> list[AllergenType]:
    """
    Semantic extraction of allergens from freetext.
    'nuts and dairy' → [AllergenType.TREE_NUTS, AllergenType.DAIRY]
    'none'           → [AllergenType.NONE]
    """
    if not raw:
        return [AllergenType.NONE]
    text = raw.lower().strip()
    if text in _NO_ALLERGY_PHRASES:
        return [AllergenType.NONE]

    found: list[AllergenType] = []
    for allergen, keywords in _ALLERGEN_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            found.append(allergen)

    # "nuts" alone should trigger tree nuts, not legumes (common ambiguity)
    if "nuts" in text and AllergenType.TREE_NUTS not in found:
        found.append(AllergenType.TREE_NUTS)

    return found if found else [AllergenType.NONE]


def _parse_age(raw: str) -> Optional[int]:
    m = re.search(r"\b(\d{1,3})\b", raw)
    if m:
        age = int(m.group(1))
        return age if 10 <= age <= 120 else None
    return None


# ══════════════════════════════════════════════
# STAGE 4 — ONTOLOGY MAPPING
# Normalized strings → typed enums
# ══════════════════════════════════════════════
def _map_diet(raw: str) -> DietType:
    return _DIET_ALIASES.get(raw.lower().strip(), DietType.UNKNOWN)


def _map_goal(raw: str) -> GoalType:
    key = raw.lower().strip()
    # Try exact match first, then prefix match
    if key in _GOAL_ALIASES:
        return _GOAL_ALIASES[key]
    for alias, goal in _GOAL_ALIASES.items():
        if alias in key:
            return goal
    return GoalType.GENERAL_HEALTH


def _map_mood(raw: str, stress_level: int) -> MoodState:
    base = _MOOD_ALIASES.get(raw.lower().strip(), MoodState.NEUTRAL)
    # Elevate to CRITICAL_LOW if low mood under high stress
    if base == MoodState.LOW and stress_level >= 7:
        return MoodState.CRITICAL_LOW
    return base


def _map_sleep_quality(raw: str, sleep_hours: Optional[float]) -> SleepQuality:
    base = _SLEEP_QUALITY_ALIASES.get(raw.lower().strip(), SleepQuality.OKAY)
    # Elevate to CRITICAL if poor quality AND fewer than 5 hours
    if base == SleepQuality.POOR and sleep_hours is not None and sleep_hours < 5:
        return SleepQuality.CRITICAL
    return base


def _map_stress(level: int) -> StressState:
    if level >= 9: return StressState.CRITICAL
    if level >= 7: return StressState.HIGH
    if level >= 5: return StressState.MODERATE
    return StressState.LOW


def _map_energy(level: int) -> EnergyState:
    if level <= 2: return EnergyState.CRITICAL_LOW
    if level <= 4: return EnergyState.LOW
    if level <= 6: return EnergyState.MODERATE
    if level <= 8: return EnergyState.HIGH
    return EnergyState.OPTIMAL


def _map_budget(raw: str) -> BudgetTier:
    return _BUDGET_ALIASES.get(raw.lower().strip(), BudgetTier.MEDIUM)


def _map_kitchen(raw: str) -> KitchenAccess:
    normalized = raw.lower().strip()
    for key, val in _KITCHEN_ALIASES:
        if key in normalized:
            return val
    # If something is provided but unrecognized, assume shared kitchen
    return KitchenAccess.SHARED_KITCHEN if normalized else KitchenAccess.FULL_KITCHEN


# ══════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════
def parse_profile(raw: dict) -> ParsedProfile:
    """
    Run the full 4-stage validation pipeline on a raw profile dict.
    Returns a ParsedProfile with fully typed, validated entities.

    Stage 1 — Sanitize:    coerce None/numbers to str, cap length
    Stage 2 — Normalize:   parse scales, extract sleep hours
    Stage 3 — Semantic:    extract allergen entities from freetext
    Stage 4 — Ontology:    map all strings to typed enums
    """
    # ── Stage 1 ────────────────────────────────
    s = _sanitize(raw)

    # ── Stage 2 ────────────────────────────────
    stress_level = _parse_scale(s.get("stress_level", "5")) or 5
    energy_level = _parse_scale(s.get("energy_level", "5")) or 5
    sleep_hours  = _parse_sleep_hours(s.get("sleep_schedule", ""))

    # ── Stage 3 ────────────────────────────────
    allergens = _parse_allergens(s.get("allergies", "none"))

    # ── Stage 4 ────────────────────────────────
    diet_type      = _map_diet(s.get("diet_type", ""))
    goal           = _map_goal(s.get("goal", "general health"))
    mood_state     = _map_mood(s.get("mood", "neutral"), stress_level)
    sleep_quality  = _map_sleep_quality(s.get("sleep_quality", "okay"), sleep_hours)
    stress_state   = _map_stress(stress_level)
    energy_state   = _map_energy(energy_level)
    budget_tier    = _map_budget(s.get("budget", "medium"))
    kitchen_access = _map_kitchen(s.get("cooking_access", ""))
    age            = _parse_age(s.get("age", ""))

    # Compound upgrade: low budget + no kitchen → CRITICAL_LOW budget
    if budget_tier == BudgetTier.LOW and kitchen_access == KitchenAccess.NONE:
        budget_tier = BudgetTier.CRITICAL_LOW

    return ParsedProfile(
        name           = s.get("name", "User") or "User",
        age            = age,
        gender         = s.get("gender", "unknown"),
        diet_type      = diet_type,
        allergens      = allergens,
        goal           = goal,
        stress_state   = stress_state,
        energy_state   = energy_state,
        sleep_quality  = sleep_quality,
        mood_state     = mood_state,
        budget_tier    = budget_tier,
        kitchen_access = kitchen_access,
        stress_level   = stress_level,
        energy_level   = energy_level,
        sleep_hours    = sleep_hours,
        raw            = raw,
    )
