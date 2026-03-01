"""
HealthOS — Meal Swap Engine  (model/meal_swap.py)
==================================================
Finds nutritionally equivalent substitutes for a food a user dislikes,
can't access, or is allergic to.

Core logic:
  1. Parse the rejected food from natural language ("I hate lentils")
  2. Look up its macro/micro profile from the nutrition index
  3. Score every candidate food in the DB by nutritional similarity
  4. Hard-filter through ConstraintGraph (diet + allergens)
  5. Rank by: protocol match → macro similarity → calorie match
  6. Return a formatted swap block for AI injection

Public API:
  find_swaps(rejected: str, constraint_graph, protocols, n=5) -> list[SwapResult]
  format_swap_block(rejected: str, swaps: list[SwapResult]) -> str
  detect_swap_request(text: str) -> str | None   # "swap lentils" → "lentils"
"""
from __future__ import annotations

import re
import math
from dataclasses import dataclass, field
from typing import Optional

# ── Lazy imports (nutrition_db must be loaded before calling find_swaps) ──────
import nutrition_db


# ══════════════════════════════════════════════
# SWAP TRIGGER DETECTION
# ══════════════════════════════════════════════

# Patterns that signal a swap request in chat
_SWAP_PATTERNS: list[tuple[re.Pattern, int]] = [
    (re.compile(r"(?:swap|replace|substitute|alternative[s]?\s+(?:for|to)|instead\s+of)\s+(?:the\s+)?(.+?)(?:\s*[,\.\?!]|$)", re.I), 1),
    (re.compile(r"(?:i\s+)?(?:hate|dislike|can'?t\s+eat|don'?t\s+(?:like|want|have)|allergic\s+to|avoid)\s+(?:the\s+)?(.+?)(?:\s*[,\.\?!]|$)", re.I), 1),
    (re.compile(r"(?:no|without|not)\s+(?:the\s+)?(.+?)(?:\s*[,\.\?!]|$)", re.I), 1),
    (re.compile(r"give\s+me\s+something\s+(?:other|else|different)\s+(?:than|instead\s+of)\s+(?:the\s+)?(.+?)(?:\s*[,\.\?!]|$)", re.I), 1),
]

# Stop words — words that aren't food names
_STOP_WORDS = {
    "it", "this", "that", "food", "meal", "thing", "option", "something",
    "anything", "everything", "more", "less", "much", "many",
}


def detect_swap_request(text: str) -> Optional[str]:
    """
    Detect if a user message is requesting a food swap.
    Returns the rejected food name (lowercase, stripped), or None.

    Examples:
      "I hate lentils"          → "lentils"
      "swap the oat porridge"   → "oat porridge"
      "no salmon please"        → "salmon"
      "what's for dinner?"      → None
    """
    for pattern, group in _SWAP_PATTERNS:
        m = pattern.search(text.strip())
        if m:
            candidate = m.group(group).strip().lower()
            # Remove trailing punctuation / filler words
            candidate = re.sub(r"[,\.\?!]+$", "", candidate).strip()
            candidate = re.sub(r"\b(please|ok|okay|though|btw)\b", "", candidate, flags=re.I).strip()
            if candidate and candidate not in _STOP_WORDS and len(candidate) > 1:
                return candidate
    return None


# ══════════════════════════════════════════════
# NUTRITIONAL SIMILARITY SCORING
# ══════════════════════════════════════════════

# Nutrients used for similarity comparison and their weights
_SIMILARITY_WEIGHTS: dict[str, float] = {
    "calories":      0.20,
    "protein_g":     0.25,
    "carbs_g":       0.15,
    "fat_g":         0.10,
    "fiber_g":       0.10,
    "iron_mg":       0.04,
    "magnesium_mg":  0.04,
    "calcium_mg":    0.03,
    "tryptophan_mg": 0.04,
    "vitamin_b12_ug":0.03,
    "zinc_mg":       0.02,
}

# Tolerance bands — how much % difference is still "similar"
_TOLERANCE: dict[str, float] = {
    "calories":      0.30,   # within 30%
    "protein_g":     0.25,
    "carbs_g":       0.35,
    "fat_g":         0.40,
    "fiber_g":       0.50,
    "default":       0.50,
}


def _nutrient_similarity(ref: dict, candidate: dict) -> float:
    """
    Compute a 0–1 similarity score between two per-100g food records.
    Uses weighted cosine-style comparison across key nutrients.
    """
    total_weight = 0.0
    weighted_score = 0.0

    for nutrient, weight in _SIMILARITY_WEIGHTS.items():
        ref_val = ref.get(nutrient) or 0.0
        cand_val = candidate.get(nutrient) or 0.0

        if ref_val == 0 and cand_val == 0:
            # Both zero → perfect match on this nutrient
            weighted_score += weight
            total_weight += weight
            continue

        if ref_val == 0 or cand_val == 0:
            # One zero, one not → partial mismatch
            total_weight += weight
            continue

        # Ratio similarity: 1.0 when identical, approaches 0 when very different
        ratio = min(ref_val, cand_val) / max(ref_val, cand_val)
        weighted_score += weight * ratio
        total_weight += weight

    return round(weighted_score / total_weight, 3) if total_weight > 0 else 0.0


def _protocol_overlap(ref_tags: list[str], cand_tags: list[str]) -> float:
    """Fraction of the reference food's protocol tags shared by the candidate."""
    proto_tags = {t for t in ref_tags if "_protocol" in t or t in (
        "high_protein", "high_fiber", "iron_rich", "magnesium_rich",
        "tryptophan_rich", "b12_rich", "zinc_rich", "calcium_rich",
        "low_calorie", "energy_dense",
    )}
    if not proto_tags:
        return 0.5   # neutral if ref has no protocol tags
    cand_set = set(cand_tags or [])
    shared = proto_tags & cand_set
    return round(len(shared) / len(proto_tags), 2)


# ══════════════════════════════════════════════
# SWAP RESULT
# ══════════════════════════════════════════════

@dataclass
class SwapResult:
    name:              str
    similarity_score:  float           # 0–1, nutritional similarity to rejected food
    protocol_overlap:  float           # 0–1, protocol tag overlap
    final_score:       float           # weighted composite
    record:            dict = field(repr=False)   # full nutrition record (per-100g)
    why:               str  = ""                  # human-readable reason


# ══════════════════════════════════════════════
# PRACTICAL FOOD FILTER
# ══════════════════════════════════════════════

# Phrases that indicate USDA research / Alaska Native / exotic entries
# that are nutritionally real but never appear in normal meal planning
_UNPRACTICAL_MARKERS: tuple[str, ...] = (
    "(alaska native)",
    "(american indian)",
    "(navajo)",
    "(native)",
    ", raw",
    ", headless",
    ", whole",
    ", roe",
    ", liver",
    ", organs",
    ", gizzard",
    ", tongue",
    ", brain",
    ", heart",
    ", kidney",
    "native food",
)

# Minimum number of protocol/nutrition tags a food must have to be a
# practical recommendation (avoids raw ingredient research entries)
_MIN_USEFUL_TAGS = 1


def _is_practical_food(record: dict) -> bool:
    """
    Return True if this food is a practical meal recommendation.
    Filters out USDA research entries and highly exotic items.
    """
    name_lower = (record.get("name") or "").lower()
    # Skip obvious research entries
    if any(marker in name_lower for marker in _UNPRACTICAL_MARKERS):
        return False
    # Must have at least one nutrition tag
    tags = record.get("tags") or []
    if len(tags) < _MIN_USEFUL_TAGS:
        return False
    return True




def find_swaps(
    rejected_name: str,
    constraint_graph=None,
    active_protocols: Optional[list[str]] = None,
    n: int = 5,
) -> list[SwapResult]:
    """
    Find the top-n constraint-safe nutritional substitutes for a rejected food.

    rejected_name:    natural language food name (e.g. "lentils", "oat porridge")
    constraint_graph: ConstraintGraph — used to filter forbidden foods
    active_protocols: user's active protocols — boosts protocol-matching foods
    n:                number of results to return

    Returns list[SwapResult] sorted best-first.
    Returns empty list if rejected food not found or DB not loaded.
    """
    if not nutrition_db.is_loaded():
        return []

    # ── 1. Resolve rejected food record ───────────────────────
    ref = nutrition_db.lookup(rejected_name)
    if not ref:
        # Try fuzzy match
        candidates = nutrition_db.fuzzy_search(rejected_name, top_n=3)
        if candidates:
            ref = candidates[0]
        else:
            # Try keyword search
            results = nutrition_db.search_by_keyword(rejected_name.split()[0], top_n=5)
            if results:
                ref = results[0]
    if not ref:
        return []

    ref_name = ref.get("name", "").lower()
    ref_tags = ref.get("tags") or []

    # ── 2. Build protocol tag set for boosting ─────────────────
    proto_boost_tags: set[str] = set(ref_tags)
    if active_protocols:
        for p in active_protocols[:5]:
            proto_boost_tags.add(p)
            proto_boost_tags.add(p.replace("_protocol", "_rich"))

    # ── 3. Score all candidate foods ───────────────────────────
    all_foods: dict = nutrition_db._db.get("foods", {})
    results: list[SwapResult] = []

    for fname, record in all_foods.items():
        # Skip the rejected food itself and close name matches
        if ref_name in fname or fname in ref_name:
            continue
        if rejected_name.lower() in fname:
            continue

        # ── Practical food filter ────────────────────────────
        if not _is_practical_food(record):
            continue

        # ── Constraint graph filter ──────────────────────────
        if constraint_graph is not None and not constraint_graph.allows_food(record):
            continue

        # ── Score ────────────────────────────────────────────
        sim   = _nutrient_similarity(ref, record)
        proto = _protocol_overlap(list(proto_boost_tags), record.get("tags") or [])

        # Composite: 60% nutritional similarity, 40% protocol overlap
        final = round(sim * 0.60 + proto * 0.40, 3)

        if final < 0.15:   # skip very poor matches
            continue

        # ── Build explanation ─────────────────────────────────
        why_parts = []
        ref_cal  = ref.get("calories", 0) or 0
        cand_cal = record.get("calories", 0) or 0
        if ref_cal and cand_cal:
            diff_pct = abs(ref_cal - cand_cal) / ref_cal * 100
            why_parts.append(f"~{cand_cal:.0f} kcal/100g ({diff_pct:.0f}% calorie diff)")

        ref_prot  = ref.get("protein_g", 0) or 0
        cand_prot = record.get("protein_g", 0) or 0
        if ref_prot and cand_prot:
            why_parts.append(f"protein {cand_prot:.1f}g vs {ref_prot:.1f}g")

        shared_protos = [
            t.replace("_protocol", "").replace("_rich", " rich")
            for t in (record.get("tags") or [])
            if t in proto_boost_tags
        ]
        if shared_protos:
            why_parts.append(f"matches: {', '.join(shared_protos[:3])}")

        results.append(SwapResult(
            name             = record.get("name", fname),
            similarity_score = sim,
            protocol_overlap = proto,
            final_score      = final,
            record           = record,
            why              = " | ".join(why_parts) if why_parts else "nutritionally similar",
        ))

    # ── 4. Sort and return top-n ───────────────────────────────
    results.sort(key=lambda r: r.final_score, reverse=True)
    return results[:n]


# ══════════════════════════════════════════════
# PROMPT BLOCK FORMATTER
# ══════════════════════════════════════════════

def format_swap_block(rejected: str, swaps: list[SwapResult],
                      constraint_graph=None) -> str:
    """
    Format swap results as a structured block for AI injection.
    The AI uses this to explain the swap and give the user context.
    """
    if not swaps:
        diet_note = ""
        if constraint_graph is not None:
            diet = constraint_graph.profile.diet_type.value
            diet_note = f" (within {diet} constraints)"
        return (
            f"\n⚠️  SWAP REQUEST: No suitable substitute found for '{rejected}'{diet_note}.\n"
            "   Ask the user what macros/protocols they want to preserve, "
            "then suggest a manual alternative."
        )

    lines = [
        f"\n🔄  MEAL SWAP: '{rejected}' → top substitutes",
    ]
    if constraint_graph is not None:
        allergens = [a.value for a in constraint_graph.profile.allergens
                     if a.value != "none"]
        diet = constraint_graph.profile.diet_type.value
        lines.append(f"   Filtered for: {diet}" +
                     (f" | allergen-free: {', '.join(allergens)}" if allergens else ""))

    lines.append("")
    for i, swap in enumerate(swaps, 1):
        rec   = swap.record
        cal   = rec.get("calories",  0) or 0
        prot  = rec.get("protein_g", 0) or 0
        carbs = rec.get("carbs_g",   0) or 0
        fat   = rec.get("fat_g",     0) or 0
        fiber = rec.get("fiber_g",   0) or 0
        score_pct = int(swap.final_score * 100)
        lines.append(
            f"   {i}. {swap.name}  [{score_pct}% match]\n"
            f"      {cal:.0f} kcal | P{prot:.1f}g C{carbs:.1f}g F{fat:.1f}g Fb{fiber:.1f}g\n"
            f"      Why: {swap.why}"
        )

    lines += [
        "",
        "   INSTRUCTION: Present these options to the user with brief explanations.",
        "   Ask which one fits their schedule/taste and confirm the swap.",
    ]
    return "\n".join(lines)
