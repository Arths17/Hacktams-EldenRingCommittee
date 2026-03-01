"""
HealthOS — Nutrition Database Engine  (v2)
Upgrades: Threshold Engine · Context Scaling Layer · Protocol Mapping Layer

Loads nutrition_index.json (built by train.py) and provides:
  - Nutrient Threshold Engine  → classify deficient / adequate / optimal / excessive
  - Context Scaling Layer      → per-100g values → realistic meal portions
  - Protocol Mapping Layer     → user state → nutrient gaps → food protocols
  - Fast exact + fuzzy food lookup
  - Compact context block for Gemini injection
"""

import os
import re
import json
import difflib
from typing import Optional, List, Dict, Tuple

INDEX_PATH = os.path.join(os.path.dirname(__file__), "nutrition_index.json")

_db: dict = {}
_loaded: bool = False


# ══════════════════════════════════════════════
# 1.  NUTRIENT THRESHOLD ENGINE
#     Daily RDA-based targets (adult 19-30)
#     Source: NIH / Dietary Reference Intakes
# ══════════════════════════════════════════════
NUTRIENT_THRESHOLDS: dict[str, dict] = {
    "calories":       {"deficient": 1400, "adequate": 1800, "optimal": 2200, "excessive": 3500},
    "protein_g":      {"deficient": 40,   "adequate": 60,   "optimal": 80,   "excessive": 200},
    "carbs_g":        {"deficient": 100,  "adequate": 200,  "optimal": 275,  "excessive": 450},
    "fat_g":          {"deficient": 30,   "adequate": 50,   "optimal": 78,   "excessive": 130},
    "fiber_g":        {"deficient": 15,   "adequate": 25,   "optimal": 38,   "excessive": 60},
    "sugar_g":        {"deficient": 0,    "adequate": 25,   "optimal": 36,   "excessive": 50},
    "iron_mg":        {"deficient": 8,    "adequate": 14,   "optimal": 18,   "excessive": 45},
    "magnesium_mg":   {"deficient": 200,  "adequate": 320,  "optimal": 420,  "excessive": 700},
    "calcium_mg":     {"deficient": 600,  "adequate": 800,  "optimal": 1000, "excessive": 2500},
    "zinc_mg":        {"deficient": 6,    "adequate": 8,    "optimal": 11,   "excessive": 40},
    "potassium_mg":   {"deficient": 2000, "adequate": 3000, "optimal": 4700, "excessive": 6000},
    "sodium_mg":      {"deficient": 0,    "adequate": 500,  "optimal": 1500, "excessive": 2300},
    "tryptophan_mg":  {"deficient": 150,  "adequate": 250,  "optimal": 350,  "excessive": 1000},
    "vitamin_c_mg":   {"deficient": 30,   "adequate": 60,   "optimal": 90,   "excessive": 2000},
    "vitamin_b12_ug": {"deficient": 1.0,  "adequate": 1.8,  "optimal": 2.4,  "excessive": 100},
    "vitamin_d_ug":   {"deficient": 5,    "adequate": 10,   "optimal": 15,   "excessive": 100},
    "vitamin_b6_mg":  {"deficient": 0.5,  "adequate": 1.0,  "optimal": 1.3,  "excessive": 100},
    "choline_mg":     {"deficient": 200,  "adequate": 350,  "optimal": 550,  "excessive": 3500},
}

# Status display helpers
STATUS_ICONS = {
    "DEFICIENT": "🔴",
    "ADEQUATE":  "🟡",
    "OPTIMAL":   "🟢",
    "EXCESSIVE": "🟠",
    "UNKNOWN":   "⚪",
}


def classify_nutrient(key: str, daily_value: float) -> str:
    """Classify a daily intake value → DEFICIENT / ADEQUATE / OPTIMAL / EXCESSIVE."""
    t = NUTRIENT_THRESHOLDS.get(key)
    if not t:
        return "UNKNOWN"
    if daily_value <= t["deficient"]:
        return "DEFICIENT"
    if daily_value <= t["adequate"]:
        return "ADEQUATE"
    if daily_value <= t["optimal"]:
        return "OPTIMAL"
    return "EXCESSIVE"


def percent_of_optimal(key: str, daily_value: float) -> float:
    """How far along (0–1+) the user is toward their daily optimal."""
    t = NUTRIENT_THRESHOLDS.get(key)
    if not t or t["optimal"] == 0:
        return 0.0
    return round(daily_value / t["optimal"], 2)


# ══════════════════════════════════════════════
# 2.  CONTEXT SCALING LAYER
#     per-100g values → realistic meal portions
# ══════════════════════════════════════════════

# Default typical meal portions (grams) when serving_size is absent
TYPICAL_PORTIONS: dict[str, float] = {
    "default":   150.0,
    "egg":        60.0,
    "bread":      30.0,
    "cheese":     30.0,
    "butter":     10.0,
    "oil":        14.0,
    "nuts":       28.0,
    "seeds":      28.0,
    "milk":      240.0,
    "yogurt":    200.0,
    "rice":      180.0,
    "pasta":     180.0,
    "oat":       160.0,
    "meat":      120.0,
    "chicken":   120.0,
    "fish":      120.0,
    "salmon":    120.0,
    "tuna":      100.0,
    "bean":      130.0,
    "lentil":    130.0,
    "spinach":    85.0,
    "broccoli":   85.0,
    "apple":     182.0,
    "banana":    118.0,
    "orange":    130.0,
}


def parse_serving_grams(serving_str: str, food_name: str = "") -> float:
    """
    Extract the gram value from a serving size string.
    Falls back to TYPICAL_PORTIONS then the 150g default.
    Examples handled:
        "100 g"  →  100
        "1 cup (240 g)"  →  240
        "3 oz (85g)"  →  85
    """
    if serving_str:
        s = str(serving_str)
        # Parenthesised grams:  "1 cup (240 g)"
        m = re.search(r'\((\d+(?:\.\d+)?)\s*g', s, re.IGNORECASE)
        if m:
            return float(m.group(1))
        # Leading grams:  "100 g" or "100g"
        m = re.search(r'^(\d+(?:\.\d+)?)\s*g', s, re.IGNORECASE)
        if m:
            return float(m.group(1))
        # Any grams mention
        m = re.search(r'(\d+(?:\.\d+)?)\s*g(?:rams?)?', s, re.IGNORECASE)
        if m:
            v = float(m.group(1))
            if 5 <= v <= 2000:   # sanity check
                return v

    # Fall back to food-name hints
    fname = food_name.lower()
    for keyword, grams in TYPICAL_PORTIONS.items():
        if keyword != "default" and keyword in fname:
            return grams

    return TYPICAL_PORTIONS["default"]


def scale_to_portion(record: dict, portion_g: Optional[float] = None) -> dict:
    """
    Return a new record with every numeric nutrient scaled from per-100g
    to the food's actual serving size (or a custom portion_g override).
    Adds 'portion_g' and 'scale_factor' metadata.
    """
    serving_g = portion_g if portion_g is not None else parse_serving_grams(
        record.get("serving_size", ""), record.get("name", "")
    )
    factor = serving_g / 100.0

    scaled = {
        "name":         record["name"],
        "portion_g":    serving_g,
        "scale_factor": round(factor, 3),
    }
    skip = {"name", "serving_size", "tags", "portion_g", "scale_factor"}
    for key, val in record.items():
        if key in skip:
            continue
        if isinstance(val, (int, float)):
            scaled[key] = round(val * factor, 2)

    scaled["tags"] = record.get("tags", [])
    return scaled


# ══════════════════════════════════════════════
# 3.  PROTOCOL MAPPING LAYER
#     user state → nutrient gaps → protocols
# ══════════════════════════════════════════════

# Map: nutrient below threshold → protocol needed
NUTRIENT_PROTOCOL_MAP: dict[str, str] = {
    "iron_mg":        "energy_protocol",
    "magnesium_mg":   "stress_protocol",
    "protein_g":      "muscle_protocol",
    "fiber_g":        "gut_protocol",
    "tryptophan_mg":  "sleep_protocol",
    "vitamin_b12_ug": "energy_protocol",
    "vitamin_b6_mg":  "mood_protocol",
    "zinc_mg":        "mood_protocol",
    "choline_mg":     "mood_protocol",
    "calcium_mg":     "bone_protocol",
    "vitamin_c_mg":   "bone_protocol",
    "vitamin_d_ug":   "bone_protocol",
}

# Map: user profile state → likely nutrient deficiency keys
STATE_DEFICIENCY_MAP: Dict[str, List[str]] = {
    "low_energy":    ["iron_mg", "vitamin_b12_ug", "vitamin_b6_mg", "protein_g"],
    "high_stress":   ["magnesium_mg", "vitamin_c_mg", "vitamin_b6_mg"],
    "poor_sleep":    ["tryptophan_mg", "magnesium_mg"],
    "low_mood":      ["zinc_mg", "vitamin_b12_ug", "choline_mg", "vitamin_b6_mg"],
    "fat_loss":      ["protein_g", "fiber_g"],
    "muscle_gain":   ["protein_g", "calories"],
    "general":       ["fiber_g", "protein_g"],
}


def user_protocol_gaps(profile: dict) -> Dict[str, str]:
    """
    Infer which nutrient protocols the user needs most,
    based on their reported state and goals.

    Returns: {protocol_name: human_readable_reason}
    """
    try:
        energy = int(re.sub(r"[^\d]", "", str(profile.get("energy_level", 5))) or 5)
    except (ValueError, TypeError):
        energy = 5
    try:
        stress = int(re.sub(r"[^\d]", "", str(profile.get("stress_level", 5))) or 5)
    except (ValueError, TypeError):
        stress = 5

    sleep_q = profile.get("sleep_quality", "okay").lower()
    mood    = profile.get("mood", "neutral").lower()
    goal    = profile.get("goal", "general health").lower()

    # Collect active states
    active_states: List[str] = []
    if energy <= 4:   active_states.append("low_energy")
    if stress >= 7:   active_states.append("high_stress")
    if sleep_q == "poor": active_states.append("poor_sleep")
    if mood == "low": active_states.append("low_mood")
    if "fat loss" in goal or "weight loss" in goal: active_states.append("fat_loss")
    if "muscle" in goal or "bulk" in goal:          active_states.append("muscle_gain")
    active_states.append("general")   # always include baseline

    # Map states → deficient nutrients → protocols
    protocols: dict[str, str] = {}
    nutrient_reasons: Dict[str, List[str]] = {}
    for state in active_states:
        for nutrient in STATE_DEFICIENCY_MAP.get(state, []):
            protocol = NUTRIENT_PROTOCOL_MAP.get(nutrient)
            if protocol:
                nutrient_reasons.setdefault(protocol, [])
                state_label = state.replace("_", " ")
                nutrient_label = nutrient.replace("_", " ").replace(" g", "g").replace(" mg", "mg")
                reason = f"{state_label} → {nutrient_label} likely low"
                if reason not in nutrient_reasons[protocol]:
                    nutrient_reasons[protocol].append(reason)

    for protocol, reasons in nutrient_reasons.items():
        protocols[protocol] = " | ".join(reasons[:2])

    return protocols


# ══════════════════════════════════════════════
# DB LOAD / LOOKUP
# ══════════════════════════════════════════════
def load(path: str = INDEX_PATH) -> bool:
    global _db, _loaded
    if _loaded:
        return True
    if not os.path.exists(path):
        return False
    with open(path, "r") as f:
        _db = json.load(f)
    _loaded = True
    return True


def is_loaded() -> bool:
    return _loaded


def meta() -> dict:
    return _db.get("meta", {})


def lookup(name: str) -> Optional[dict]:
    """Exact case-insensitive food lookup (returns per-100g record)."""
    return _db.get("foods", {}).get(name.lower().strip())


def lookup_scaled(name: str, portion_g: Optional[float] = None) -> Optional[dict]:
    """Lookup and immediately scale to serving portion."""
    rec = lookup(name)
    return scale_to_portion(rec, portion_g) if rec else None


def fuzzy_search(query: str, top_n: int = 5) -> list[dict]:
    """Fuzzy search — returns list of matching per-100g food records."""
    foods = _db.get("foods", {})
    matches = difflib.get_close_matches(query.lower().strip(), list(foods.keys()), n=top_n, cutoff=0.45)
    return [foods[m] for m in matches]


def search_by_keyword(keyword: str, top_n: int = 10) -> list[dict]:
    """Substring keyword search across all food names."""
    kw = keyword.lower().strip()
    return [rec for key, rec in _db.get("foods", {}).items() if kw in key][:top_n]


PROTOCOL_TAGS: dict[str, str] = {
    "stress":          "stress_protocol",
    "energy":          "energy_protocol",
    "sleep":           "sleep_protocol",
    "gut":             "gut_protocol",
    "muscle":          "muscle_protocol",
    "fat_loss":        "fat_loss_protocol",
    "muscle_gain":     "muscle_gain_protocol",
    "mood":            "mood_protocol",
    "bone":            "bone_protocol",
    "high_protein":    "high_protein",
    "low_calorie":     "low_calorie",
    "high_fiber":      "high_fiber",
    "magnesium":       "magnesium_rich",
    "iron":            "iron_rich",
    "tryptophan":      "tryptophan_rich",
    "b12":             "b12_rich",
    "zinc":            "zinc_rich",
    "calcium":         "calcium_rich",
}


def get_protocol_foods(protocol: str, top_n: int = 10) -> list[dict]:
    """Return top_n per-100g food records for a given protocol."""
    tag = PROTOCOL_TAGS.get(protocol.lower(), protocol.lower() + "_protocol")
    food_names = _db.get("tag_index", {}).get(tag, [])[:top_n]
    foods = _db.get("foods", {})
    return [foods[n.lower()] for n in food_names if n.lower() in foods]


# ══════════════════════════════════════════════
# FORMATTING HELPERS
# ══════════════════════════════════════════════
def _format_food(rec: dict, scaled: bool = True) -> str:
    """
    One-line food summary.
    If scaled=True, values are assumed to already be per-serving.
    If scaled=False, auto-scales from per-100g first.
    """
    if not scaled:
        rec = scale_to_portion(rec)

    name     = rec.get("name", "Unknown")
    portion  = rec.get("portion_g", 100)
    cal      = rec.get("calories",  "?")
    prot     = rec.get("protein_g",  0)
    carbs    = rec.get("carbs_g",    0)
    fat      = rec.get("fat_g",      0)
    fiber    = rec.get("fiber_g",    0)

    line = f"{name} ({portion}g): {cal} kcal | P:{prot}g C:{carbs}g F:{fat}g"

    micros = []
    for field, label in [
        ("magnesium_mg",  "Mg"),
        ("iron_mg",       "Fe"),
        ("tryptophan_mg", "Trp"),
        ("vitamin_b12_ug","B12"),
        ("zinc_mg",       "Zn"),
        ("calcium_mg",    "Ca"),
        ("vitamin_c_mg",  "VitC"),
    ]:
        v = rec.get(field)
        if v:
            micros.append(f"{label}:{v}")
    if fiber:
        micros.append(f"Fiber:{fiber}g")
    if micros:
        line += f" | {', '.join(micros)}"

    tags = [t for t in rec.get("tags", []) if "_protocol" in t or t in
            ("high_protein", "high_fiber", "magnesium_rich", "iron_rich",
             "tryptophan_rich", "b12_rich", "low_calorie")]
    if tags:
        line += f"  [{', '.join(tags)}]"

    return line


def _threshold_summary(profile: dict) -> str:
    """
    Build a concise nutrient gap block for the AI based on user state.
    Shows which nutrients are likely deficient and their daily targets.
    """
    gaps = user_protocol_gaps(profile)
    if not gaps:
        return ""

    lines = [
        "\n  NUTRIENT GAP ANALYSIS:",
        "  (Based on your reported state vs. daily optimal targets)",
    ]
    shown_nutrients: set[str] = set()
    for protocol, reason in gaps.items():
        # find nutrients that drive this protocol
        nutrients = [k for k, v in NUTRIENT_PROTOCOL_MAP.items() if v == protocol]
        for nut in nutrients:
            if nut in shown_nutrients:
                continue
            shown_nutrients.add(nut)
            t = NUTRIENT_THRESHOLDS.get(nut, {})
            optimal = t.get("optimal", "?")
            deficient = t.get("deficient", "?")
            unit = "g" if nut.endswith("_g") else ("µg" if nut.endswith("_ug") else "mg")
            clean = nut.replace("_g", "").replace("_mg", "").replace("_ug", "").replace("_", " ").title()
            lines.append(
                f"    • {clean}: optimal = {optimal}{unit}/day | "
                f"deficient below {deficient}{unit} | Protocol: {protocol}"
            )
    return "\n".join(lines)


# ══════════════════════════════════════════════
# MAIN CONTEXT BUILDER
# ══════════════════════════════════════════════
def build_nutrition_context(profile: dict) -> str:
    """
    Builds the full nutrition knowledge block injected into the AI seed message.
    Includes: gap analysis, threshold context, scaled per-serving food lists.
    """
    if not _loaded:
        return ""

    goal    = profile.get("goal", "general health").lower()
    stress  = int(re.sub(r"[^\d]", "", str(profile.get("stress_level", 5))) or 5)
    energy  = int(re.sub(r"[^\d]", "", str(profile.get("energy_level", 5))) or 5)
    sleep_q = profile.get("sleep_quality", "okay").lower()
    diet    = profile.get("diet_type", "omnivore").lower()
    mood    = profile.get("mood", "neutral").lower()

    is_veg  = "vegan" in diet or "vegetarian" in diet
    meat_kw = ["chicken", "beef", "pork", "turkey", "salmon", "tuna",
               "fish", "lamb", "bacon", "shrimp", "crab"]

    lines = [
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"  NUTRITION DATABASE  ({meta().get('total_foods', '?'):,} foods · scaled to real portions)",
        "  Source: Kaggle — Nutritional Values for Common Foods",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # ── Nutrient Gap Analysis ──────────────────
    lines.append(_threshold_summary(profile))

    # ── Threshold reference table ──────────────
    lines += [
        "\n  DAILY NUTRIENT TARGETS (for meal plan construction):",
    ]
    key_nutrients = [
        ("protein_g", "Protein"), ("fiber_g", "Fiber"), ("iron_mg", "Iron"),
        ("magnesium_mg", "Magnesium"), ("calcium_mg", "Calcium"),
        ("tryptophan_mg", "Tryptophan"), ("vitamin_b12_ug", "Vitamin B12"),
        ("zinc_mg", "Zinc"),
    ]
    for key, label in key_nutrients:
        t = NUTRIENT_THRESHOLDS.get(key, {})
        unit = "g" if key.endswith("_g") else ("µg" if key.endswith("_ug") else "mg")
        lines.append(
            f"    {label:<15} deficient<{t.get('deficient','?')}{unit}  "
            f"adequate={t.get('adequate','?')}{unit}  "
            f"optimal={t.get('optimal','?')}{unit}"
        )

    # ── Protocol food sections ─────────────────
    gaps = user_protocol_gaps(profile)

    sections: list[tuple[str, str]] = []

    # Priority order: critical states first
    if energy <= 4:
        sections.append(("⚡ Energy Restoration (Iron · B12 · B6)", "energy"))
    if stress >= 7:
        sections.append(("😰 Stress Relief (Magnesium · Complex Carbs)", "stress"))
    if sleep_q == "poor":
        sections.append(("😴 Sleep Support (Tryptophan · Low Sugar)", "sleep"))
    if mood == "low":
        sections.append(("💆 Mood Support (Zinc · B12 · Choline)", "mood"))

    # Goal-based
    if "fat loss" in goal or "weight loss" in goal:
        sections.append(("🎯 Fat Loss (High Protein · Low Calorie)", "fat_loss"))
    elif "muscle" in goal or "bulk" in goal:
        sections.append(("🎯 Muscle Gain (Very High Protein · Calorie Dense)", "muscle_gain"))
    else:
        sections.append(("🎯 High-Protein Options", "high_protein"))

    # Always include gut health
    sections.append(("🌿 Gut Health (High Fiber)", "gut"))

    for section_title, protocol in sections:
        foods_100g = get_protocol_foods(protocol, top_n=10)
        if not foods_100g:
            continue

        # Vegetarian/vegan filter
        if is_veg:
            foods_100g = [f for f in foods_100g
                          if not any(kw in f.get("name", "").lower() for kw in meat_kw)]

        # Scale to real portions
        foods_scaled = [scale_to_portion(f) for f in foods_100g[:6]]

        lines.append(f"\n  {section_title}:")
        for rec in foods_scaled:
            lines.append(f"    • {_format_food(rec, scaled=True)}")

    lines += [
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  INSTRUCTIONS FOR AI:",
        "  1. Reference foods by name and their SCALED (per-serving) values above.",
        "  2. Use NUTRIENT TARGETS to classify meals as deficient/adequate/optimal.",
        "  3. Build meal plans that hit OPTIMAL daily targets for the flagged nutrients.",
        "  4. Explain WHY each food was chosen (which protocol it addresses).",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
    ]

    return "\n".join(lines)


