"""
HealthOS — Unified Constraint Graph  (model/constraint_graph.py)
=================================================================
Single source of truth for ALL constraint queries across every module.

Before: each module filters independently
    meal planner      → checks diet string
    food recommender  → checks diet string again
    nutrition engine  → checks diet string again
    (inconsistencies guaranteed)

After: one ConstraintGraph, every module queries the same state
    cg = ConstraintGraph.from_parsed_profile(pp)
    cg.allows_food(record)         → bool
    cg.filter_foods(foods_dict)    → filtered dict
    cg.active_protocols            → ranked list[str]
    cg.critical_flags              → list[str]
    cg.to_prompt_block()           → str (AI injection)

Usage:
    from validation import parse_profile
    from constraint_graph import ConstraintGraph
    pp = parse_profile(raw_dict)
    cg = ConstraintGraph.from_parsed_profile(pp)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from ontology import (
    ParsedProfile,
    DietType, AllergenType, GoalType,
    StressState, EnergyState, SleepQuality, MoodState,
    BudgetTier, KitchenAccess,
)


# ══════════════════════════════════════════════
# DIET → FORBIDDEN KEYWORD SET
# ══════════════════════════════════════════════
_DIET_FORBIDDEN: dict[DietType, frozenset[str]] = {
    DietType.VEGETARIAN: frozenset({
        "chicken", "beef", "pork", "turkey", "salmon", "tuna", "fish",
        "lamb", "bacon", "shrimp", "crab", "lobster", "venison", "duck",
        "goose", "ham", "sausage", "pepperoni", "anchovies", "sardine",
        "tilapia", "cod", "halibut", "herring", "mackerel", "prawn",
    }),
    DietType.VEGAN: frozenset({
        # All meat
        "chicken", "beef", "pork", "turkey", "salmon", "tuna", "fish",
        "lamb", "bacon", "shrimp", "crab", "lobster", "venison", "duck",
        "ham", "sausage", "pepperoni", "anchovies", "sardine",
        # All animal products
        "milk", "cheese", "butter", "cream", "yogurt", "whey",
        "egg", "honey", "gelatin", "lard",
    }),
    DietType.PESCATARIAN: frozenset({
        "chicken", "beef", "pork", "turkey", "lamb", "bacon", "duck",
        "ham", "sausage", "pepperoni", "venison", "goose",
    }),
    DietType.HALAL: frozenset({
        "pork", "ham", "bacon", "lard", "pepperoni", "gelatin",
    }),
    DietType.KOSHER: frozenset({
        "pork", "ham", "bacon", "shrimp", "crab", "lobster",
        "clam", "oyster", "shellfish",
    }),
    DietType.KETO: frozenset(),         # Handled by macro filter, not keyword
    DietType.PALEO: frozenset({
        "dairy", "milk", "cheese", "grain", "bread", "pasta", "rice", "oat",
    }),
    DietType.GLUTEN_FREE: frozenset({
        "wheat", "barley", "rye", "bread", "pasta", "flour",
    }),
    DietType.OMNIVORE: frozenset(),
    DietType.UNKNOWN:  frozenset(),
}


# ══════════════════════════════════════════════
# ALLERGEN → FORBIDDEN KEYWORD SET
# ══════════════════════════════════════════════
_ALLERGEN_FORBIDDEN: dict[AllergenType, frozenset[str]] = {
    AllergenType.GLUTEN:    frozenset({"wheat", "barley", "rye", "bread", "pasta", "flour", "gluten"}),
    AllergenType.DAIRY:     frozenset({"milk", "cheese", "butter", "cream", "yogurt", "whey", "dairy"}),
    AllergenType.EGGS:      frozenset({"egg", "eggs", "mayonnaise"}),
    AllergenType.PEANUTS:   frozenset({"peanut", "peanuts", "groundnut"}),
    AllergenType.TREE_NUTS: frozenset({"almond", "walnut", "cashew", "pecan",
                                        "pistachio", "hazelnut", "macadamia", "nut"}),
    AllergenType.SOY:       frozenset({"soy", "soya", "tofu", "edamame", "tempeh"}),
    AllergenType.FISH:      frozenset({"salmon", "tuna", "cod", "tilapia", "halibut",
                                        "sardine", "anchovies", "fish", "herring"}),
    AllergenType.SHELLFISH: frozenset({"shrimp", "prawn", "crab", "lobster",
                                        "clam", "oyster", "scallop", "mussel", "shellfish"}),
    AllergenType.WHEAT:     frozenset({"wheat", "bread", "pasta", "flour", "cereal"}),
    AllergenType.SESAME:    frozenset({"sesame", "tahini"}),
    AllergenType.LEGUMES:   frozenset({"legume", "lentil", "chickpea", "bean", "pea"}),
    AllergenType.LACTOSE:   frozenset({"milk", "cream", "yogurt", "cheese", "butter"}),
    AllergenType.FRUCTOSE:  frozenset({"apple", "pear", "mango", "fructose", "corn syrup"}),
    AllergenType.SULFITES:  frozenset({"wine", "dried fruit", "vinegar"}),
    AllergenType.NONE:      frozenset(),
}


# ══════════════════════════════════════════════
# STATE → PROTOCOL ACTIVATION TABLE
# Maps typed state enum values → which protocols they activate
# ══════════════════════════════════════════════
_STATE_PROTOCOLS: dict[str, list[str]] = {
    # Stress
    StressState.CRITICAL.value: [
        "stress_protocol", "magnesium_protocol", "sleep_protocol",
        "mood_protocol", "blood_sugar_protocol",
    ],
    StressState.HIGH.value: [
        "stress_protocol", "sleep_protocol", "mood_protocol",
    ],
    StressState.MODERATE.value: ["stress_protocol"],

    # Energy
    EnergyState.CRITICAL_LOW.value: [
        "energy_protocol", "iron_protocol", "b_complex_protocol",
        "hydration_protocol",
    ],
    EnergyState.LOW.value: ["energy_protocol", "b_complex_protocol"],

    # Sleep
    SleepQuality.CRITICAL.value: [
        "sleep_protocol", "tryptophan_protocol", "magnesium_protocol",
        "anti_caffeine_protocol",
    ],
    SleepQuality.POOR.value: ["sleep_protocol", "tryptophan_protocol"],

    # Mood
    MoodState.CRITICAL_LOW.value: [
        "mood_protocol", "stress_protocol", "gut_protocol",
        "cognitive_protocol",
    ],
    MoodState.LOW.value: ["mood_protocol", "gut_protocol"],

    # Goal
    GoalType.FAT_LOSS.value: [
        "fat_loss_protocol", "blood_sugar_protocol", "gut_protocol",
    ],
    GoalType.MUSCLE_GAIN.value: [
        "muscle_protocol", "recovery_protocol", "performance_protocol",
    ],
    GoalType.GENERAL_HEALTH.value: [
        "immune_protocol", "gut_protocol", "anti_inflammatory_protocol",
    ],
    GoalType.MAINTENANCE.value: [
        "gut_protocol", "heart_protocol", "immune_protocol",
    ],

    # Budget / kitchen
    BudgetTier.CRITICAL_LOW.value: ["emergency_meals_protocol"],
    KitchenAccess.NONE.value:       ["no_cook_protocol"],
    KitchenAccess.MICROWAVE_ONLY.value: ["microwave_protocol"],
}


# ══════════════════════════════════════════════
# CONSTRAINT GRAPH
# ══════════════════════════════════════════════
@dataclass
class ConstraintGraph:
    """
    Unified constraint graph. Built ONCE from a ParsedProfile.
    Every module queries this object instead of re-deriving constraints.
    """
    profile: ParsedProfile

    _forbidden_keywords: frozenset[str] = field(default_factory=frozenset)
    _active_protocols:   list[str]      = field(default_factory=list)
    _critical_flags:     list[str]      = field(default_factory=list)

    # ── Factory ──────────────────────────────────────────────────
    @classmethod
    def from_parsed_profile(cls, pp: ParsedProfile) -> "ConstraintGraph":
        cg = cls(profile=pp)
        cg._forbidden_keywords = cg._build_forbidden_keywords()
        cg._active_protocols   = cg._build_active_protocols()
        cg._critical_flags     = list(pp.active_critical_flags)

        # Write derived sets back into ParsedProfile for backward compat
        pp.forbidden_food_keywords = cg._forbidden_keywords
        pp.forbidden_categories    = frozenset(
            a.value for a in pp.allergens if a != AllergenType.NONE
        )
        return cg

    # ── Internal builders ─────────────────────────────────────────
    def _build_forbidden_keywords(self) -> frozenset[str]:
        banned: set[str] = set()
        banned |= _DIET_FORBIDDEN.get(self.profile.diet_type, frozenset())
        for allergen in self.profile.allergens:
            if allergen != AllergenType.NONE:
                banned |= _ALLERGEN_FORBIDDEN.get(allergen, frozenset())
        return frozenset(banned)

    def _build_active_protocols(self) -> list[str]:
        seen:   set[str]  = set()
        protos: list[str] = []

        def _add(key: str) -> None:
            for p in _STATE_PROTOCOLS.get(key, []):
                if p not in seen:
                    seen.add(p)
                    protos.append(p)

        pp = self.profile
        # Priority order: most critical states first
        _add(pp.stress_state.value)
        _add(pp.energy_state.value)
        _add(pp.sleep_quality.value)
        _add(pp.mood_state.value)
        _add(pp.goal.value)
        _add(pp.budget_tier.value)
        _add(pp.kitchen_access.value)

        # Ensure baseline protocols are always present
        for must_have in ("sleep_protocol", "stress_protocol", "energy_protocol"):
            if must_have not in seen:
                protos.append(must_have)
                seen.add(must_have)

        return protos

    # ── Public query API ──────────────────────────────────────────
    def allows_food(self, food_record: dict) -> bool:
        """
        Returns True if this food passes ALL constraint checks.
        Checks: allergens, diet exclusions, forbidden keywords.
        """
        if not food_record:
            return False
        name     = (food_record.get("name") or "").lower()
        tags_str = " ".join(food_record.get("tags") or []).lower()
        combined = name + " " + tags_str
        return not any(kw in combined for kw in self._forbidden_keywords)

    def filter_foods(self, foods: dict) -> dict:
        """Filter a {name: record} dict through the constraint graph."""
        return {k: v for k, v in foods.items() if self.allows_food(v)}

    @property
    def active_protocols(self) -> list[str]:
        return list(self._active_protocols)

    @property
    def forbidden_keywords(self) -> frozenset[str]:
        return self._forbidden_keywords

    @property
    def critical_flags(self) -> list[str]:
        return list(self._critical_flags)

    @property
    def is_critical(self) -> bool:
        return bool(self._critical_flags)

    def to_prompt_block(self) -> str:
        """
        Generate explicit LLM-directive constraint block for injection at the
        TOP of the system prompt.  Uses imperative language so the model treats
        these as hard rules, not suggestions.
        """
        pp = self.profile

        lines = [
            "",
            "╔══════════════════════════════════════════════════════════════╗",
            "║  ⚠️  HARD USER CONSTRAINTS — ENFORCE BEFORE GENERATING ANYTHING  ║",
            "╚══════════════════════════════════════════════════════════════╝",
        ]

        # ── Diet + Allergens (identity block) ──────────────────────────────
        diet_str = pp.diet_type.value.upper()
        lines.append(f"  DIET TYPE : {diet_str}")
        if pp.allergens and AllergenType.NONE not in pp.allergens:
            allergen_str = ", ".join(a.value.upper() for a in pp.allergens)
            lines.append(f"  ALLERGENS : {allergen_str}")
        else:
            lines.append("  ALLERGENS : none")

        # ── Absolute food prohibition ───────────────────────────────────────
        if self._forbidden_keywords:
            all_kw = sorted(self._forbidden_keywords)
            # Wrap into rows of 8 for readability
            rows   = [all_kw[i:i+8] for i in range(0, len(all_kw), 8)]
            lines += [
                "",
                "  🚫 ABSOLUTE FOOD PROHIBITIONS",
                "     The following foods/ingredients MUST NEVER appear in any",
                "     recommendation, meal plan, recipe, snack list, food example,",
                "     or substitution suggestion — even as 'for others' options:",
                "",
            ]
            for row in rows:
                lines.append("     " + ",  ".join(row))
            lines += [
                "",
                "     If a food CONTAINS, IS MADE FROM, or IS DERIVED FROM any",
                "     of the above, it is also FORBIDDEN.",
            ]

        # ── Critical health state flags ─────────────────────────────────────
        if self._critical_flags:
            lines += [
                "",
                "  🔴 CRITICAL HEALTH STATES — ADDRESS THESE FIRST:",
            ]
            for flag in self._critical_flags:
                lines.append(f"     • {flag}")

        # ── Active protocols ────────────────────────────────────────────────
        lines += [
            "",
            "  🎯 ACTIVE PROTOCOLS (priority order):",
            "     " + ",  ".join(self._active_protocols),
        ]

        # ── Context summary ─────────────────────────────────────────────────
        lines += [
            "",
            "  📋 USER CONTEXT:",
            f"     goal={pp.goal.value}  |  "
            f"stress={pp.stress_level}/10  |  "
            f"energy={pp.energy_level}/10  |  "
            f"sleep={pp.sleep_quality.value}"
            + (f" ({pp.sleep_hours}h)" if pp.sleep_hours else ""),
            f"     budget={pp.budget_tier.value}  |  kitchen={pp.kitchen_access.value}",
            "",
            "╚══════════════════════════════════════════════════════════════╝",
            "",
        ]

        return "\n".join(lines)
