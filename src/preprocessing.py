"""
Ingredient parsing and label analysis.

Turns raw Open Food Facts text ("Sugar, Palm Oil, Cocoa (12%)...") into a
clean list of ingredients, detects additives / allergens / dietary flags, and
computes a transparent, rule-based nutrition risk score. No LLM is required
for any of this — it is deterministic and auditable.
"""

from __future__ import annotations

import re

# --- Reference knowledge (small, curated, and explainable) -----------------

# Common allergen keywords grouped by allergen family.
ALLERGEN_KEYWORDS = {
    "milk": ["milk", "lactose", "casein", "whey", "butter", "cream", "cheese"],
    "eggs": ["egg", "albumin"],
    "peanuts": ["peanut", "groundnut"],
    "tree nuts": ["almond", "cashew", "hazelnut", "walnut", "pistachio", "pecan", "nut"],
    "soy": ["soy", "soya", "soybean"],
    "gluten": ["wheat", "barley", "rye", "gluten", "malt", "semolina"],
    "fish": ["fish", "anchovy", "cod", "tuna"],
    "shellfish": ["shrimp", "prawn", "crab", "lobster", "shellfish"],
    "sesame": ["sesame", "tahini"],
}

# Ingredients that indicate a product is NOT vegan / NOT vegetarian.
NON_VEGAN_KEYWORDS = [
    "milk", "lactose", "casein", "whey", "butter", "cream", "cheese",
    "egg", "honey", "gelatin", "gelatine", "carmine", "lard", "shellac",
    "fish", "meat", "chicken", "beef", "pork", "anchovy",
]
NON_VEGETARIAN_KEYWORDS = [
    "gelatin", "gelatine", "fish", "meat", "chicken", "beef", "pork",
    "anchovy", "lard", "rennet",
]

# A short list of additives worth flagging in plain English.
ADDITIVES_OF_INTEREST = {
    "e621": "monosodium glutamate (MSG) - flavour enhancer",
    "e951": "aspartame - artificial sweetener",
    "e950": "acesulfame-K - artificial sweetener",
    "e102": "tartrazine - artificial colour",
    "e110": "sunset yellow - artificial colour",
    "e129": "allura red - artificial colour",
    "e211": "sodium benzoate - preservative",
    "e250": "sodium nitrite - preservative (cured meats)",
    "palm oil": "palm oil - saturated fat / sustainability concern",
    "high fructose corn syrup": "high fructose corn syrup - added sugar",
    "hydrogenated": "hydrogenated oil - possible trans fats",
}

# Per-100g thresholds broadly aligned with UK FSA front-of-pack "high" labels.
NUTRITION_THRESHOLDS = {
    "sugars_100g": {"high": 22.5, "moderate": 5.0, "label": "sugar"},
    "salt_100g": {"high": 1.5, "moderate": 0.3, "label": "salt"},
    "saturated_fat_100g": {"high": 5.0, "moderate": 1.5, "label": "saturated fat"},
    "fat_100g": {"high": 17.5, "moderate": 3.0, "label": "total fat"},
}


def parse_ingredients(ingredients_text: str) -> list[str]:
    """Split a raw ingredients string into a clean list of ingredient names."""
    if not ingredients_text:
        return []
    # Normalise separators, drop percentages and bracketed sub-lists' noise.
    text = ingredients_text.replace(";", ",").replace("\n", " ")
    parts = re.split(r",|\band\b", text, flags=re.IGNORECASE)
    cleaned = []
    for part in parts:
        item = re.sub(r"\([^)]*\)", "", part)      # remove ( ... )
        item = re.sub(r"\d+(\.\d+)?\s*%", "", item)  # remove 12%
        item = item.strip(" .*_-")
        if item and len(item) > 1:
            cleaned.append(item.lower())
    return cleaned


def detect_allergens(product: dict) -> list[str]:
    """Return a de-duplicated list of allergen families found in the product."""
    haystack = " ".join([
        product.get("ingredients_text", ""),
        product.get("allergens", ""),
        product.get("traces", ""),
    ]).lower()

    found = []
    for allergen, keywords in ALLERGEN_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(k)}", haystack) for k in keywords):
            found.append(allergen)
    return found


def detect_additives(ingredients_text: str) -> list[str]:
    """Return plain-English descriptions of notable additives present."""
    text = (ingredients_text or "").lower()
    hits = []
    for key, description in ADDITIVES_OF_INTEREST.items():
        if key in text:
            hits.append(description)
    return hits


def dietary_flags(product: dict) -> dict:
    """Determine vegan / vegetarian status from ingredients and labels."""
    text = " ".join([
        product.get("ingredients_text", ""),
        product.get("labels", ""),
    ]).lower()

    label_says_vegan = "vegan" in (product.get("labels", "") or "").lower()
    label_says_vegetarian = "vegetarian" in (product.get("labels", "") or "").lower()

    non_vegan_hit = next((w for w in NON_VEGAN_KEYWORDS if re.search(rf"\b{w}", text)), None)
    non_veg_hit = next((w for w in NON_VEGETARIAN_KEYWORDS if re.search(rf"\b{w}", text)), None)

    is_vegan = label_says_vegan or (non_vegan_hit is None)
    is_vegetarian = label_says_vegetarian or (non_veg_hit is None)

    return {
        "vegan": is_vegan,
        "vegetarian": is_vegetarian,
        "non_vegan_reason": non_vegan_hit,
        "non_vegetarian_reason": non_veg_hit,
    }


def nutrition_assessment(product: dict) -> list[dict]:
    """
    Rate each key nutrient as low / moderate / high per 100g.
    Returns a list of {nutrient, value, level, message} dicts.
    """
    results = []
    for key, cfg in NUTRITION_THRESHOLDS.items():
        value = product.get(key)
        if value is None:
            continue
        if value >= cfg["high"]:
            level = "high"
        elif value >= cfg["moderate"]:
            level = "moderate"
        else:
            level = "low"
        results.append({
            "nutrient": cfg["label"],
            "value": value,
            "level": level,
            "message": f"{cfg['label'].capitalize()} is {level} ({value} g per 100g).",
        })
    return results


def compute_risk_score(product: dict) -> dict:
    """
    Combine additives, nutrition and processing level into a 0-100 risk score.
    Higher = more reasons for a health-conscious shopper to pause. Fully
    transparent: every point added is recorded in `reasons`.
    """
    score = 0
    reasons = []

    # Nutrition contribution.
    for item in nutrition_assessment(product):
        if item["level"] == "high":
            score += 15
            reasons.append(f"High {item['nutrient']} (+15)")
        elif item["level"] == "moderate":
            score += 6
            reasons.append(f"Moderate {item['nutrient']} (+6)")

    # Additives contribution.
    additives = detect_additives(product.get("ingredients_text", ""))
    for add in additives:
        score += 5
        reasons.append(f"Additive: {add} (+5)")

    # NOVA ultra-processing contribution.
    nova = product.get("nova_group")
    try:
        nova = int(float(nova)) if nova is not None else None
    except (TypeError, ValueError):
        nova = None
    if nova == 4:
        score += 15
        reasons.append("Ultra-processed food (NOVA group 4) (+15)")
    elif nova == 3:
        score += 8
        reasons.append("Processed food (NOVA group 3) (+8)")

    # Nutri-Score contribution (D or E is a red flag).
    grade = (product.get("nutriscore_grade") or "").lower()
    if grade in ("d", "e"):
        score += 10
        reasons.append(f"Poor Nutri-Score ({grade.upper()}) (+10)")

    score = min(score, 100)

    if score >= 60:
        band = "high"
    elif score >= 30:
        band = "moderate"
    else:
        band = "low"

    return {"score": score, "band": band, "reasons": reasons}


def build_label_analysis(product: dict) -> dict:
    """Run every deterministic analysis step and return a single summary dict."""
    return {
        "ingredients": parse_ingredients(product.get("ingredients_text", "")),
        "allergens": detect_allergens(product),
        "additives": detect_additives(product.get("ingredients_text", "")),
        "dietary": dietary_flags(product),
        "nutrition": nutrition_assessment(product),
        "risk": compute_risk_score(product),
    }
