"""
HealthOS — Nutrition Data Training Pipeline
Downloads the Kaggle nutritional values dataset and builds a local
nutrition_index.json used by the AI model at runtime.

Run once:  .venv/bin/python train.py
"""

import os
import re
import json
import glob
import pathlib
import kagglehub
import pandas as pd

OUTPUT_FILE = "model/nutrition_index.json"

# ─────────────────────────────────────────────
# COLUMN NORMALISATION MAP
# Maps raw CSV column names → standard keys used throughout HealthOS
# ─────────────────────────────────────────────
COL_MAP = {
    # name
    "name":                         "name",
    # serving
    "serving_size":                 "serving_size",
    # calories
    "calories":                     "calories",
    # macros — exact column names from this CSV (underscore_format)
    "protein":                      "protein_g",
    "total_fat":                    "fat_g",
    "fat":                          "fat_g",
    "carbohydrate":                 "carbs_g",
    "fiber":                        "fiber_g",
    "sugars":                       "sugar_g",
    # micros — exact column names (note typos: irom, zink are in the source data)
    "sodium":                       "sodium_mg",
    "irom":                         "iron_mg",      # typo in dataset
    "iron":                         "iron_mg",
    "calcium":                      "calcium_mg",
    "vitamin_c":                    "vitamin_c_mg",
    "vitamin_b12":                  "vitamin_b12_ug",
    "magnesium":                    "magnesium_mg",
    "potassium":                    "potassium_mg",
    "zink":                         "zinc_mg",       # typo in dataset
    "zinc":                         "zinc_mg",
    "tryptophan":                   "tryptophan_mg",
    # bonus columns available in this dataset
    "caffeine":                     "caffeine_mg",
    "choline":                      "choline_mg",
    "vitamin_b6":                   "vitamin_b6_mg",
    "vitamin_d":                    "vitamin_d_ug",
    "water":                        "water_g",
}

# ─────────────────────────────────────────────
# PER-100g SIGNIFICANCE THRESHOLDS
# Values at which a food is a meaningful source of each nutrient
# (calibrated as ~10-30% of daily optimal per 100g)
# ─────────────────────────────────────────────
PER100G = {
    "protein_g":      {"source": 5,    "rich": 15,   "very_rich": 25},
    "fiber_g":        {"source": 2,    "rich": 5,    "very_rich": 10},
    "iron_mg":        {"source": 1,    "rich": 2,    "very_rich": 5},
    "magnesium_mg":   {"source": 20,   "rich": 50,   "very_rich": 100},
    "calcium_mg":     {"source": 80,   "rich": 150,  "very_rich": 300},
    "tryptophan_mg":  {"source": 0.05, "rich": 0.1,  "very_rich": 0.25},
    "vitamin_b12_ug": {"source": 0.5,  "rich": 1.0,  "very_rich": 2.0},
    "zinc_mg":        {"source": 1,    "rich": 2,    "very_rich": 5},
    "potassium_mg":   {"source": 100,  "rich": 250,  "very_rich": 500},
    "vitamin_c_mg":   {"source": 10,   "rich": 30,   "very_rich": 60},
    "vitamin_b6_mg":  {"source": 0.1,  "rich": 0.3,  "very_rich": 0.6},
    "choline_mg":     {"source": 20,   "rich": 50,   "very_rich": 100},
}

# ─────────────────────────────────────────────
# HEALTH TAG RULES
# Each food gets auto-tagged based on threshold classification.
# Protocol tags are derived from nutrient profile, not hardcoded.
# ─────────────────────────────────────────────
def auto_tag(row: dict) -> list:
    tags = []
    th   = PER100G

    cal  = row.get("calories",      0) or 0
    prot = row.get("protein_g",     0) or 0
    fat  = row.get("fat_g",         0) or 0
    carbs= row.get("carbs_g",       0) or 0
    fiber= row.get("fiber_g",       0) or 0
    sugar= row.get("sugar_g",       0) or 0
    mag  = row.get("magnesium_mg",  0) or 0
    iron = row.get("iron_mg",       0) or 0
    tryp = row.get("tryptophan_mg", 0) or 0
    b12  = row.get("vitamin_b12_ug",0) or 0
    zinc = row.get("zinc_mg",       0) or 0
    calc = row.get("calcium_mg",    0) or 0
    potk = row.get("potassium_mg",  0) or 0
    vitc = row.get("vitamin_c_mg",  0) or 0
    b6   = row.get("vitamin_b6_mg", 0) or 0
    chol = row.get("choline_mg",    0) or 0

    # ── Macro quality tags ──────────────────────────────────────
    if prot >= th["protein_g"]["very_rich"]: tags.append("very_high_protein")
    if prot >= th["protein_g"]["rich"]:      tags.append("high_protein")
    if prot >= th["protein_g"]["source"]:    tags.append("protein_source")

    if fiber >= th["fiber_g"]["very_rich"]:  tags.append("very_high_fiber")
    if fiber >= th["fiber_g"]["rich"]:       tags.append("high_fiber")
    if fiber >= th["fiber_g"]["source"]:     tags.append("fiber_source")

    if carbs >= 30:                          tags.append("complex_carb_source")
    if sugar <= 5 and carbs <= 25:           tags.append("low_sugar")
    if fat <= 3:                             tags.append("low_fat")
    if cal <= 150:                           tags.append("low_calorie")
    if cal >= 400:                           tags.append("calorie_dense")

    # ── Micro quality tags ──────────────────────────────────────
    if iron >= th["iron_mg"]["rich"]:             tags.append("iron_rich")
    if mag  >= th["magnesium_mg"]["rich"]:        tags.append("magnesium_rich")
    if tryp >= th["tryptophan_mg"]["rich"]:       tags.append("tryptophan_rich")
    if b12  >= th["vitamin_b12_ug"]["rich"]:      tags.append("b12_rich")
    if zinc >= th["zinc_mg"]["rich"]:             tags.append("zinc_rich")
    if calc >= th["calcium_mg"]["rich"]:          tags.append("calcium_rich")
    if potk >= th["potassium_mg"]["rich"]:        tags.append("potassium_rich")
    if vitc >= th["vitamin_c_mg"]["rich"]:        tags.append("vitamin_c_rich")
    if b6   >= th["vitamin_b6_mg"]["rich"]:       tags.append("b6_rich")
    if chol >= th["choline_mg"]["rich"]:          tags.append("choline_rich")

    # ── Protocol tags (nutrient-driven logic) ───────────────────
    # stress_protocol: magnesium calms nervous system; complex carbs stabilise cortisol
    if "magnesium_rich" in tags or "complex_carb_source" in tags:
        tags.append("stress_protocol")

    # energy_protocol: iron/B12/B6 combat fatigue; protein sustains output
    if "iron_rich" in tags or "b12_rich" in tags or "b6_rich" in tags:
        tags.append("energy_protocol")

    # sleep_protocol: tryptophan → serotonin → melatonin precursor
    if "tryptophan_rich" in tags:
        tags.append("sleep_protocol")

    # gut_protocol: fiber feeds microbiome
    if "high_fiber" in tags or "very_high_fiber" in tags:
        tags.append("gut_protocol")

    # muscle_protocol: high protein + adequate calories
    if "high_protein" in tags and cal >= 150:
        tags.append("muscle_protocol")

    # fat_loss_protocol: protein preserves muscle; low cal creates deficit
    if "protein_source" in tags and "low_calorie" in tags:
        tags.append("fat_loss_protocol")

    # mood_protocol: zinc/B12/potassium support neurotransmitter synthesis
    if "zinc_rich" in tags or "b12_rich" in tags or "choline_rich" in tags:
        tags.append("mood_protocol")

    # muscle_gain_protocol (high calorie + very high protein)
    if "very_high_protein" in tags and "calorie_dense" in tags:
        tags.append("muscle_gain_protocol")

    # bone_protocol: calcium + vitamin C (collagen)
    if "calcium_rich" in tags or "vitamin_c_rich" in tags:
        tags.append("bone_protocol")

    return tags


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────
def build_nutrition_index():
    print("📥  Downloading Kaggle dataset…")
    path = kagglehub.dataset_download(
        "trolukovich/nutritional-values-for-common-foods-and-products"
    )
    print(f"✅  Downloaded to: {path}\n")

    # Find the CSV file(s)
    csv_files = glob.glob(os.path.join(path, "**", "*.csv"), recursive=True)
    if not csv_files:
        raise FileNotFoundError(f"No CSV found in {path}")

    csv_path = csv_files[0]
    print(f"📄  Using: {csv_path}")

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"    Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"    Columns: {list(df.columns)}\n")

    # Normalise column names to lowercase
    df.columns = [c.strip().lower() for c in df.columns]
    rename = {c: COL_MAP[c] for c in df.columns if c in COL_MAP}
    df = df.rename(columns=rename)

    # Drop duplicate column names that arise when multiple raw columns map to
    # the same target (e.g. both 'total_fat' and 'fat' → 'fat_g')
    df = df.loc[:, ~df.columns.duplicated(keep="first")]

    if "name" not in df.columns:
        raise ValueError("Could not find a food name column in dataset. "
                         "Add it to COL_MAP.")

    # Drop rows with no name; clean string
    df = df.dropna(subset=["name"])
    df["name"] = df["name"].astype(str).str.strip()

    # Build keep_cols: only mapped target columns that exist, deduplicated (preserving order)
    seen = set()
    keep_cols = ["name"]
    for v in COL_MAP.values():
        if v != "name" and v in df.columns and v not in seen:
            keep_cols.append(v)
            seen.add(v)
    df = df[keep_cols].copy()

    # Convert numeric columns to float.
    # Many values are stored as unit-annotated strings e.g. "9.17 g", "2.53 mg".
    # Strip everything except the leading number before parsing.
    numeric_cols = [c for c in keep_cols if c != "name"]
    for col in numeric_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.extract(r"([\d]*\.?[\d]+)")[0]   # pull out the numeric part
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Build index dict: lowercase name → record
    index = {}
    for _, row in df.iterrows():
        food_name = row["name"]
        record = {"name": food_name}
        for col in numeric_cols:
            val = round(float(row[col]), 2)
            if val != 0:
                record[col] = val
        record["tags"] = auto_tag(record)
        index[food_name.lower()] = record

    # Also build a tag → [food_names] reverse index for fast protocol lookups
    tag_index: dict = {}
    for food_key, record in index.items():
        for tag in record.get("tags", []):
            tag_index.setdefault(tag, [])
            if len(tag_index[tag]) < 30:   # cap at 30 per tag
                tag_index[tag].append(record["name"])

    output = {
        "meta": {
            "source": "trolukovich/nutritional-values-for-common-foods-and-products",
            "total_foods": len(index),
            "columns": numeric_cols,
        },
        "foods": index,
        "tag_index": tag_index,
    }

    # Save
    pathlib.Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"💾  Saved nutrition index → {OUTPUT_FILE}")
    print(f"    Foods indexed : {len(index):,}")
    print(f"    Protocol tags : {list(tag_index.keys())}")


if __name__ == "__main__":
    build_nutrition_index()
