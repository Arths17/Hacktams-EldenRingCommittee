"""
HealthOS — Semantic Health Ontology  (model/ontology.py)
=========================================================
Typed entities that replace raw strings throughout the pipeline.

Instead of:
    "vegetarian"  →  string match
    "allergy"     →  string blob
    "stress"      →  raw number

You get:
    diet_type     : DietType.VEGETARIAN
    allergens     : [AllergenType.TREE_NUTS, AllergenType.DAIRY]
    stress_state  : StressState.CRITICAL
    energy_state  : EnergyState.CRITICAL_LOW

All modules import from here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════
# DIET TYPE
# ══════════════════════════════════════════════
class DietType(Enum):
    OMNIVORE    = "omnivore"
    VEGETARIAN  = "vegetarian"
    VEGAN       = "vegan"
    HALAL       = "halal"
    KOSHER      = "kosher"
    PESCATARIAN = "pescatarian"
    KETO        = "keto"
    PALEO       = "paleo"
    GLUTEN_FREE = "gluten_free"
    UNKNOWN     = "unknown"


# ══════════════════════════════════════════════
# ALLERGEN TYPES  (Top-14 FDA + common extras)
# ══════════════════════════════════════════════
class AllergenType(Enum):
    GLUTEN    = "gluten"
    DAIRY     = "dairy"
    EGGS      = "eggs"
    PEANUTS   = "peanuts"
    TREE_NUTS = "tree_nuts"
    SOY       = "soy"
    FISH      = "fish"
    SHELLFISH = "shellfish"
    WHEAT     = "wheat"
    SESAME    = "sesame"
    LEGUMES   = "legumes"
    FRUCTOSE  = "fructose"
    LACTOSE   = "lactose"
    SULFITES  = "sulfites"
    NONE      = "none"


# ══════════════════════════════════════════════
# GOAL TYPE
# ══════════════════════════════════════════════
class GoalType(Enum):
    FAT_LOSS       = "fat_loss"
    MUSCLE_GAIN    = "muscle_gain"
    MAINTENANCE    = "maintenance"
    GENERAL_HEALTH = "general_health"
    UNKNOWN        = "unknown"


# ══════════════════════════════════════════════
# STATE ENUMS
# ══════════════════════════════════════════════
class StressState(Enum):
    CRITICAL = "critical"   # stress >= 9
    HIGH     = "high"       # stress 7–8
    MODERATE = "moderate"   # stress 5–6
    LOW      = "low"        # stress <= 4


class EnergyState(Enum):
    CRITICAL_LOW = "critical_low"   # energy <= 2
    LOW          = "low"            # energy 3–4
    MODERATE     = "moderate"       # energy 5–6
    HIGH         = "high"           # energy 7–8
    OPTIMAL      = "optimal"        # energy 9–10


class SleepQuality(Enum):
    CRITICAL = "critical"   # poor quality AND < 5 h
    POOR     = "poor"
    OKAY     = "okay"
    GOOD     = "good"


class MoodState(Enum):
    CRITICAL_LOW = "critical_low"   # low mood + high stress
    LOW          = "low"
    NEUTRAL      = "neutral"
    GOOD         = "good"


class BudgetTier(Enum):
    CRITICAL_LOW = "critical_low"   # low budget + no kitchen
    LOW          = "low"
    MEDIUM       = "medium"
    FLEXIBLE     = "flexible"


class KitchenAccess(Enum):
    NONE           = "none"
    MICROWAVE_ONLY = "microwave_only"
    SHARED_KITCHEN = "shared_kitchen"
    FULL_KITCHEN   = "full_kitchen"


# ══════════════════════════════════════════════
# PARSED PROFILE  — fully typed, validated snapshot
# ══════════════════════════════════════════════
@dataclass
class ParsedProfile:
    """
    Output of the validation pipeline.
    Every health-critical field is a typed entity — no raw strings.
    """
    # Identity
    name:   str           = "User"
    age:    Optional[int] = None
    gender: str           = "unknown"

    # Typed entities
    diet_type:     DietType            = DietType.OMNIVORE
    allergens:     list[AllergenType]  = field(default_factory=list)
    goal:          GoalType            = GoalType.GENERAL_HEALTH

    # Typed state
    stress_state:  StressState   = StressState.MODERATE
    energy_state:  EnergyState   = EnergyState.MODERATE
    sleep_quality: SleepQuality  = SleepQuality.OKAY
    mood_state:    MoodState     = MoodState.NEUTRAL

    # Typed constraints
    budget_tier:    BudgetTier    = BudgetTier.MEDIUM
    kitchen_access: KitchenAccess = KitchenAccess.FULL_KITCHEN

    # Validated numerics
    stress_level:  int            = 5       # 1–10
    energy_level:  int            = 5       # 1–10
    sleep_hours:   Optional[float]= None    # derived from schedule string

    # Derived constraint sets (populated by ConstraintGraph)
    forbidden_food_keywords: frozenset[str] = field(default_factory=frozenset)
    forbidden_categories:    frozenset[str] = field(default_factory=frozenset)

    # Original raw dict (kept for backward compatibility with legacy callers)
    raw: dict = field(default_factory=dict)

    # ── Convenience properties ────────────────────────────────────

    @property
    def is_vegetarian_or_vegan(self) -> bool:
        return self.diet_type in (DietType.VEGETARIAN, DietType.VEGAN)

    @property
    def is_critical(self) -> bool:
        return (
            self.stress_state  == StressState.CRITICAL     or
            self.energy_state  == EnergyState.CRITICAL_LOW or
            self.sleep_quality == SleepQuality.CRITICAL    or
            self.mood_state    == MoodState.CRITICAL_LOW
        )

    @property
    def active_critical_flags(self) -> list[str]:
        flags: list[str] = []
        if self.stress_state == StressState.CRITICAL:
            flags.append(f"CRITICAL_STRESS: {self.stress_level}/10")
        if self.energy_state == EnergyState.CRITICAL_LOW:
            flags.append(f"CRITICAL_ENERGY: {self.energy_level}/10")
        if self.sleep_quality == SleepQuality.CRITICAL:
            flags.append("CRITICAL_SLEEP: poor quality + <5 h sleep")
        if self.mood_state == MoodState.CRITICAL_LOW:
            flags.append("CRITICAL_MOOD: low mood under high stress")
        return flags

    @property
    def summary(self) -> str:
        parts = [
            f"diet={self.diet_type.value}",
            f"goal={self.goal.value}",
            f"stress={self.stress_state.value}({self.stress_level})",
            f"energy={self.energy_state.value}({self.energy_level})",
            f"sleep={self.sleep_quality.value}",
            f"mood={self.mood_state.value}",
            f"budget={self.budget_tier.value}",
            f"kitchen={self.kitchen_access.value}",
        ]
        if self.allergens and AllergenType.NONE not in self.allergens:
            parts.append("allergens=[" + ",".join(a.value for a in self.allergens) + "]")
        return "ParsedProfile(" + " | ".join(parts) + ")"
