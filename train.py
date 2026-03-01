"""
HealthOS — Nutrition Data Training Pipeline
Downloads multiple Kaggle datasets and builds:
  • model/nutrition_index.json   — merged food database (60k+ foods)
  • model/sleep_insights.json    — sleep/stress statistics
  • model/student_health.json    — college student mental health stats

Run once:  .venv/bin/python train.py
"""

import os
import re
import json
import glob
import pathlib
import kagglehub
import pandas as pd

OUTPUT_FILE          = "model/nutrition_index.json"
SLEEP_INSIGHTS_FILE  = "model/sleep_insights.json"
STUDENT_HEALTH_FILE  = "model/student_health.json"

# Max new foods to import from Open Food Facts (quality-filtered)
MAX_OFF_FOODS = 25_000

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
# DATASET 2 — OPEN FOOD FACTS
# openfoodfacts/world-food-facts
# 300k+ branded/global foods, all values per 100g
# Minerals stored as g/100g → must convert to mg/mg/µg
# Energy stored as kJ → must convert to kcal
# ─────────────────────────────────────────────
OFF_COLS = [
    "product_name", "serving_size",
    "energy_100g", "proteins_100g", "fat_100g", "carbohydrates_100g",
    "fiber_100g", "sugars_100g", "sodium_100g", "calcium_100g",
    "iron_100g", "potassium_100g", "vitamin-c_100g", "vitamin-b12_100g",
    "magnesium_100g", "zinc_100g",
]

def _load_openfoodfacts() -> dict:
    """Download Open Food Facts and return a food index dict."""
    print("\n📥  Downloading Open Food Facts (global branded foods)…")
    path = kagglehub.dataset_download("openfoodfacts/world-food-facts")
    tsv_files = glob.glob(os.path.join(path, "**", "*.tsv"), recursive=True)
    if not tsv_files:
        print("⚠️  No TSV found — skipping Open Food Facts")
        return {}

    index: dict = {}
    total = 0

    for chunk in pd.read_csv(
        tsv_files[0], sep="\t",
        usecols=lambda c: c in OFF_COLS,
        chunksize=50_000, low_memory=False, on_bad_lines="skip",
    ):
        if total >= MAX_OFF_FOODS:
            break
        chunk = chunk.dropna(subset=["product_name", "energy_100g"])
        chunk = chunk[chunk["product_name"].astype(str).str.strip() != ""]

        for _, row in chunk.iterrows():
            if total >= MAX_OFF_FOODS:
                break
            name = str(row["product_name"]).strip()
            if not name or name.lower() in index:
                continue

            # kJ → kcal
            try:
                calories = round(float(row["energy_100g"]) / 4.184, 1)
            except (ValueError, TypeError):
                continue
            if not (5 <= calories <= 900):
                continue

            record: dict = {"name": name, "calories": calories}

            # Macros (g/100g — no unit change)
            for src, dst in [
                ("proteins_100g",     "protein_g"),
                ("fat_100g",          "fat_g"),
                ("carbohydrates_100g","carbs_g"),
                ("fiber_100g",        "fiber_g"),
                ("sugars_100g",       "sugar_g"),
            ]:
                try:
                    v = float(row.get(src) or 0)
                    if v > 0:
                        record[dst] = round(v, 2)
                except (ValueError, TypeError):
                    pass

            # Minerals: g/100g → mg/100g (×1000)
            for src, dst in [
                ("sodium_100g",     "sodium_mg"),
                ("calcium_100g",    "calcium_mg"),
                ("iron_100g",       "iron_mg"),
                ("potassium_100g",  "potassium_mg"),
                ("vitamin-c_100g",  "vitamin_c_mg"),
                ("magnesium_100g",  "magnesium_mg"),
                ("zinc_100g",       "zinc_mg"),
            ]:
                try:
                    v = float(row.get(src) or 0)
                    if v > 0:
                        record[dst] = round(v * 1000, 2)
                except (ValueError, TypeError):
                    pass

            # Vitamin B12: g/100g → µg/100g (×1,000,000)
            try:
                b12 = float(row.get("vitamin-b12_100g") or 0)
                if b12 > 0:
                    record["vitamin_b12_ug"] = round(b12 * 1_000_000, 2)
            except (ValueError, TypeError):
                pass

            # Quality filter: must have at least protein or carbs
            if not record.get("protein_g") and not record.get("carbs_g"):
                continue

            record["tags"] = auto_tag(record)
            index[name.lower()] = record
            total += 1

    print(f"✅  Open Food Facts: {total:,} foods added")
    return index


# ─────────────────────────────────────────────
# DATASET 3 — SLEEP HEALTH & LIFESTYLE
# uom190346a/sleep-health-and-lifestyle-dataset
# 374 adults: sleep hours, quality, stress, activity, BMI
# ─────────────────────────────────────────────
def build_sleep_insights() -> None:
    print("\n📥  Downloading Sleep Health & Lifestyle dataset…")
    path = kagglehub.dataset_download("uom190346a/sleep-health-and-lifestyle-dataset")
    csvs = glob.glob(os.path.join(path, "**", "*.csv"), recursive=True)
    df = pd.read_csv(csvs[0])
    df.columns = [c.strip() for c in df.columns]

    insights: dict = {}

    # Sleep quality vs duration buckets
    df["sleep_bucket"] = pd.cut(
        df["Sleep Duration"], bins=[0, 5, 6, 7, 8, 24],
        labels=["<5h", "5-6h", "6-7h", "7-8h", ">8h"]
    )
    insights["sleep_quality_by_hours"] = (
        df.groupby("sleep_bucket", observed=True)["Quality of Sleep"]
        .mean().round(2).to_dict()
    )
    insights["stress_by_sleep_hours"] = (
        df.groupby("sleep_bucket", observed=True)["Stress Level"]
        .mean().round(2).to_dict()
    )

    # Physical activity vs sleep quality
    df["activity_bucket"] = pd.cut(
        df["Physical Activity Level"], bins=[0, 30, 60, 90, 200],
        labels=["low(<30min)", "moderate(30-60)", "high(60-90)", "very_high(>90)"]
    )
    insights["sleep_quality_by_activity"] = (
        df.groupby("activity_bucket", observed=True)["Quality of Sleep"]
        .mean().round(2).to_dict()
    )

    # BMI vs sleep quality
    insights["sleep_quality_by_bmi"] = (
        df.groupby("BMI Category")["Quality of Sleep"].mean().round(2).to_dict()
    )

    # % high stress (≥7) among people sleeping < 6h
    low_sleep = df[df["Sleep Duration"] < 6]
    insights["pct_high_stress_with_low_sleep"] = round(
        (low_sleep["Stress Level"] >= 7).mean() * 100, 1
    )

    # Optimal sleep for minimum stress
    best_sleep = (
        df.groupby("sleep_bucket", observed=True)["Stress Level"]
        .mean().idxmin()
    )
    insights["optimal_sleep_range_for_stress"] = str(best_sleep)

    # Occupation breakdown
    insights["sleep_by_occupation"] = (
        df.groupby("Occupation")["Sleep Duration"].mean().round(1).to_dict()
    )

    insights["meta"] = {
        "source": "uom190346a/sleep-health-and-lifestyle-dataset",
        "records": len(df),
        "summary": (
            "374 adults: sleep duration/quality, stress (1-10), "
            "physical activity, BMI, sleep disorders"
        ),
    }

    pathlib.Path(SLEEP_INSIGHTS_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(SLEEP_INSIGHTS_FILE, "w") as f:
        json.dump(insights, f, indent=2)
    print(f"✅  Sleep insights → {SLEEP_INSIGHTS_FILE}")


# ─────────────────────────────────────────────
# DATASET 4 — STUDENT MENTAL HEALTH
# shariful07/student-mental-health
# 101 university students: depression, anxiety, panic attacks
# ─────────────────────────────────────────────
def build_student_health_insights() -> None:
    print("\n📥  Downloading Student Mental Health dataset…")
    path = kagglehub.dataset_download("shariful07/student-mental-health")
    csvs = glob.glob(os.path.join(path, "**", "*.csv"), recursive=True)
    df = pd.read_csv(csvs[0])
    df.columns = [c.strip() for c in df.columns]

    insights: dict = {}

    yes = lambda col: round((df[col] == "Yes").mean() * 100, 1)

    insights["depression_prevalence_pct"]    = yes("Do you have Depression?")
    insights["anxiety_prevalence_pct"]       = yes("Do you have Anxiety?")
    insights["panic_attack_prevalence_pct"]  = yes("Do you have Panic attack?")
    insights["sought_treatment_pct"]         = yes("Did you seek any specialist for a treatment?")

    # Co-occurrence: both depression AND anxiety
    both = (
        (df["Do you have Depression?"] == "Yes") &
        (df["Do you have Anxiety?"]    == "Yes")
    )
    insights["depression_and_anxiety_pct"] = round(both.mean() * 100, 1)

    # Depression by CGPA
    insights["depression_by_cgpa"] = (
        df.groupby("What is your CGPA?")["Do you have Depression?"]
        .apply(lambda x: round((x == "Yes").mean() * 100, 1))
        .to_dict()
    )

    # Anxiety by year of study
    insights["anxiety_by_year"] = (
        df.groupby("Your current year of Study")["Do you have Anxiety?"]
        .apply(lambda x: round((x == "Yes").mean() * 100, 1))
        .to_dict()
    )

    # Gender breakdown
    insights["depression_by_gender"] = (
        df.groupby("Choose your gender")["Do you have Depression?"]
        .apply(lambda x: round((x == "Yes").mean() * 100, 1))
        .to_dict()
    )

    insights["meta"] = {
        "source": "shariful07/student-mental-health",
        "records": len(df),
        "summary": (
            "101 university students: depression, anxiety, panic attacks "
            "broken down by CGPA, year of study, and gender"
        ),
    }

    pathlib.Path(STUDENT_HEALTH_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(STUDENT_HEALTH_FILE, "w") as f:
        json.dump(insights, f, indent=2)
    print(f"✅  Student health insights → {STUDENT_HEALTH_FILE}")


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────
def build_nutrition_index():
    # ── 1. Primary dataset ────────────────────
    print("📥  Downloading primary dataset (Common Foods)…")
    path = kagglehub.dataset_download(
        "trolukovich/nutritional-values-for-common-foods-and-products"
    )
    print(f"✅  Downloaded to: {path}\n")

    csv_files = glob.glob(os.path.join(path, "**", "*.csv"), recursive=True)
    if not csv_files:
        raise FileNotFoundError(f"No CSV found in {path}")

    csv_path = csv_files[0]
    print(f"📄  Using: {csv_path}")

    df = pd.read_csv(csv_path, low_memory=False)
    print(f"    Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"    Columns: {list(df.columns)}\n")

    df.columns = [c.strip().lower() for c in df.columns]
    rename = {c: COL_MAP[c] for c in df.columns if c in COL_MAP}
    df = df.rename(columns=rename)
    df = df.loc[:, ~df.columns.duplicated(keep="first")]

    if "name" not in df.columns:
        raise ValueError("Could not find a food name column in dataset.")

    df = df.dropna(subset=["name"])
    df["name"] = df["name"].astype(str).str.strip()

    seen = set()
    keep_cols = ["name"]
    for v in COL_MAP.values():
        if v != "name" and v in df.columns and v not in seen:
            keep_cols.append(v)
            seen.add(v)
    df = df[keep_cols].copy()

    numeric_cols = [c for c in keep_cols if c != "name"]
    for col in numeric_cols:
        df[col] = (
            df[col].astype(str).str.extract(r"([\d]*\.?[\d]+)")[0]
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    index: dict = {}
    for _, row in df.iterrows():
        food_name = row["name"]
        record = {"name": food_name}
        for col in numeric_cols:
            val = round(float(row[col]), 2)
            if val != 0:
                record[col] = val
        record["tags"] = auto_tag(record)
        index[food_name.lower()] = record

    print(f"    Primary foods loaded: {len(index):,}")

    # ── 2. Open Food Facts merge ──────────────
    try:
        off_index = _load_openfoodfacts()
        before = len(index)
        for key, record in off_index.items():
            if key not in index:   # primary dataset always wins
                index[key] = record
        print(f"    Total after merge: {len(index):,} (+{len(index)-before:,} new)")
    except Exception as e:
        print(f"⚠️  Open Food Facts skipped: {e}")

    # ── 3. Tag index ──────────────────────────
    tag_index: dict = {}
    for food_key, record in index.items():
        for tag in record.get("tags", []):
            tag_index.setdefault(tag, [])
            if len(tag_index[tag]) < 50:
                tag_index[tag].append(record["name"])

    # ── 4. Save nutrition index ───────────────
    output = {
        "meta": {
            "sources": [
                "trolukovich/nutritional-values-for-common-foods-and-products",
                "openfoodfacts/world-food-facts",
            ],
            "total_foods": len(index),
            "columns": numeric_cols,
        },
        "foods": index,
        "tag_index": tag_index,
    }

    pathlib.Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n💾  Saved nutrition index → {OUTPUT_FILE}")
    print(f"    Foods indexed : {len(index):,}")
    print(f"    Protocol tags : {list(tag_index.keys())}")

    # ── 5. Sleep insights ─────────────────────
    try:
        build_sleep_insights()
    except Exception as e:
        print(f"⚠️  Sleep insights skipped: {e}")

    # ── 6. Student mental health insights ─────
    try:
        build_student_health_insights()
    except Exception as e:
        print(f"⚠️  Student health insights skipped: {e}")


if __name__ == "__main__":
    build_nutrition_index()
