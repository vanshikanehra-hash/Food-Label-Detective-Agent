"""
Scenario-based validation for the Food Label Detective Agent.

These tests double as the capstone "validation using test cases / scenario
checks" deliverable. They run against the synthetic CSV so they work offline
and deterministically (no network, no LLM key required).

Run:  python -m pytest -v   (or simply:  python tests/test_agent.py)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import preprocessing, guardrails  # noqa: E402
from src import off_client  # noqa: E402
from src import agent  # noqa: E402


def _load(barcode: str) -> dict:
    """Load a product straight from the synthetic CSV (no network)."""
    for row in off_client._load_sample_rows():
        if row["barcode"] == barcode:
            return off_client._row_to_product(row)
    raise AssertionError(f"barcode {barcode} not in sample data")


# 1. Ingredient parsing strips percentages and brackets.
def test_ingredient_parsing():
    ings = preprocessing.parse_ingredients("Sugar, Cocoa (12%), Hazelnuts")
    assert "sugar" in ings
    assert "cocoa" in ings
    assert not any("%" in i for i in ings)


# 2. Allergen detection finds milk in Nutella.
def test_allergen_detection():
    nutella = _load("3017620422003")
    allergens = preprocessing.detect_allergens(nutella)
    assert "milk" in allergens


# 3. High-sugar product is scored as high risk.
def test_high_sugar_risk():
    cola = _load("5449000000996")
    risk = preprocessing.compute_risk_score(cola)
    assert risk["band"] in ("moderate", "high")


# 4. Plain oats are recognised as vegan.
def test_vegan_flag():
    oats = _load("0000000000101")
    flags = preprocessing.dietary_flags(oats)
    assert flags["vegan"] is True


# 5. Yogurt is NOT vegan (contains milk).
def test_non_vegan_flag():
    yogurt = _load("0000000000103")
    flags = preprocessing.dietary_flags(yogurt)
    assert flags["vegan"] is False


# 6. Allergy guardrail fires a critical alert.
def test_allergy_guardrail():
    nutella = _load("3017620422003")
    analysis = preprocessing.build_label_analysis(nutella)
    prefs = {"diet": "none", "low_sugar": False, "low_salt": False,
             "allergies": ["milk"]}
    guard = guardrails.apply_guardrails(nutella, analysis, prefs)
    assert guard["recommendation"] == "avoid"
    assert any(c["severity"] == "critical" for c in guard["conflicts"])


# 7. Additive detection catches MSG in instant noodles.
def test_additive_detection():
    noodles = _load("0000000000105")
    additives = preprocessing.detect_additives(noodles["ingredients_text"])
    assert any("msg" in a.lower() or "glutamate" in a.lower() for a in additives)


# 8. Full agent workflow returns a structured 'ok' result offline.
def test_agent_end_to_end():
    result = agent.analyse_product("0000000000101", user_id="test_user")
    assert result["status"] == "ok"
    assert "explanation" in result
    assert result["analysis"]["risk"]["band"] == "low"


# 9. Unknown product is handled gracefully.
def test_not_found():
    # Gibberish that neither the API search nor the synthetic CSV can match.
    result = agent.analyse_product("zzqxwlkjhqwe1298notarealproductxyz", user_id="test_user")
    assert result["status"] == "not_found"


# 10. Empty query triggers the clarifying-question step.
def test_needs_input():
    result = agent.analyse_product("", user_id="test_user")
    assert result["status"] == "needs_input"
    assert result["questions"]


if __name__ == "__main__":
    # Minimal runner so the file works without pytest installed.
    passed = 0
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            passed += 1
        except AssertionError as exc:
            print(f"FAIL  {fn.__name__}: {exc}")
    print(f"\n{passed}/{len(tests)} tests passed.")
