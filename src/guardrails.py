"""
Safety guardrails.

This is a sensitive domain (food, allergies, health), so the agent must:
  1. Never give medical advice or make health guarantees.
  2. Loudly warn when a product conflicts with a declared allergy.
  3. Keep a human in control for the final eat / don't-eat decision.
  4. Handle missing data honestly instead of guessing.

`apply_guardrails` inspects the analysis + preferences and returns a list of
guardrail messages plus an overall recommendation the UI must present clearly.
"""

from __future__ import annotations

MEDICAL_DISCLAIMER = (
    "This tool provides general information from food labels only. It is NOT "
    "medical or dietary advice. If you have a diagnosed allergy or health "
    "condition, always confirm with the physical package and a qualified "
    "professional before eating."
)


def _preference_conflicts(analysis: dict, preferences: dict) -> list[dict]:
    """Compare the product analysis against the user's stated preferences."""
    conflicts = []

    # Allergy conflicts are the highest priority.
    user_allergies = {a.lower() for a in preferences.get("allergies", [])}
    product_allergens = {a.lower() for a in analysis.get("allergens", [])}
    overlap = user_allergies & product_allergens
    for allergen in sorted(overlap):
        conflicts.append({
            "severity": "critical",
            "type": "allergy",
            "message": f"ALLERGY ALERT: this product may contain {allergen}, "
                       f"which you asked to avoid.",
        })

    # Diet conflicts.
    diet = preferences.get("diet", "none")
    dietary = analysis.get("dietary", {})
    if diet == "vegan" and not dietary.get("vegan", True):
        reason = dietary.get("non_vegan_reason") or "an animal-derived ingredient"
        conflicts.append({
            "severity": "warning",
            "type": "diet",
            "message": f"Not vegan-friendly: contains {reason}.",
        })
    if diet == "vegetarian" and not dietary.get("vegetarian", True):
        reason = dietary.get("non_vegetarian_reason") or "a non-vegetarian ingredient"
        conflicts.append({
            "severity": "warning",
            "type": "diet",
            "message": f"Not vegetarian-friendly: contains {reason}.",
        })

    # Sugar / salt goals.
    if preferences.get("low_sugar"):
        for item in analysis.get("nutrition", []):
            if item["nutrient"] == "sugar" and item["level"] == "high":
                conflicts.append({
                    "severity": "warning",
                    "type": "nutrition",
                    "message": "High in sugar, which conflicts with your low-sugar goal.",
                })
    if preferences.get("low_salt"):
        for item in analysis.get("nutrition", []):
            if item["nutrient"] == "salt" and item["level"] == "high":
                conflicts.append({
                    "severity": "warning",
                    "type": "nutrition",
                    "message": "High in salt, which conflicts with your low-salt goal.",
                })

    return conflicts


def _data_quality_notes(product: dict, analysis: dict) -> list[dict]:
    """Flag when the label data is incomplete, so we don't over-claim."""
    notes = []
    if not product.get("ingredients_text"):
        notes.append({
            "severity": "info",
            "type": "data",
            "message": "No ingredient list was available, so allergen and diet "
                       "checks may be incomplete.",
        })
    if all(product.get(k) is None for k in
           ("sugars_100g", "salt_100g", "saturated_fat_100g", "fat_100g")):
        notes.append({
            "severity": "info",
            "type": "data",
            "message": "No nutrition values were available for this product.",
        })
    return notes


def apply_guardrails(product: dict, analysis: dict, preferences: dict) -> dict:
    """
    Produce the final guardrail package.

    Returns:
        {
          "disclaimer": str,
          "conflicts": [...],          # ordered, critical first
          "data_notes": [...],
          "recommendation": "avoid" | "caution" | "ok_to_consider",
          "human_in_the_loop": str,    # message reminding user they decide
        }
    """
    conflicts = _preference_conflicts(analysis, preferences)
    data_notes = _data_quality_notes(product, analysis)

    has_critical = any(c["severity"] == "critical" for c in conflicts)
    has_warning = any(c["severity"] == "warning" for c in conflicts)
    risk_band = analysis.get("risk", {}).get("band", "low")

    if has_critical:
        recommendation = "avoid"
    elif has_warning or risk_band == "high":
        recommendation = "caution"
    else:
        recommendation = "ok_to_consider"

    # Sort conflicts so critical items always surface first.
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    conflicts.sort(key=lambda c: severity_order.get(c["severity"], 3))

    return {
        "disclaimer": MEDICAL_DISCLAIMER,
        "conflicts": conflicts,
        "data_notes": data_notes,
        "recommendation": recommendation,
        "human_in_the_loop": (
            "This is guidance, not a decision. Please read the physical label "
            "and decide for yourself — especially for allergies."
        ),
    }
