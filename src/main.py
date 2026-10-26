"""
Command-line interface for the Food Label Detective Agent.

Examples:
    python -m src.main --query "Nutella"
    python -m src.main --query 3017620422003 --user alice
    python -m src.main --set-pref --user alice --diet vegan --low-sugar --allergy peanuts --allergy milk
    python -m src.main --show-log
"""

from __future__ import annotations

import argparse
import json

from . import agent
from . import preferences as prefs_module
from .logger import read_runs


def _print_result(result: dict) -> None:
    if result["status"] == "needs_input":
        print("I need a bit more information:")
        for q in result["questions"]:
            print(f"  - {q}")
        return

    if result["status"] == "not_found":
        print(result["message"])
        return

    product = result["product"]
    analysis = result["analysis"]
    guard = result["guardrails"]

    print("=" * 64)
    print(f"PRODUCT : {product['product_name']}  ({product.get('brands','')})")
    print(f"SOURCE  : {product['source']}")
    print(f"RISK    : {analysis['risk']['score']}/100  ({analysis['risk']['band'].upper()})")
    print(f"ADVICE  : {guard['recommendation'].replace('_', ' ').upper()}")
    print("-" * 64)
    print("EXPLANATION")
    print(result["explanation"])
    print("-" * 64)

    if guard["conflicts"]:
        print("FLAGS")
        for c in guard["conflicts"]:
            print(f"  [{c['severity'].upper()}] {c['message']}")
    if guard["data_notes"]:
        print("DATA NOTES")
        for n in guard["data_notes"]:
            print(f"  - {n['message']}")

    print("-" * 64)
    print("RISK BREAKDOWN")
    for reason in analysis["risk"]["reasons"] or ["No risk factors detected."]:
        print(f"  - {reason}")
    print("-" * 64)
    print(guard["disclaimer"])
    print(guard["human_in_the_loop"])
    print("=" * 64)


def main() -> None:
    parser = argparse.ArgumentParser(description="Food Label Detective Agent (CLI)")
    parser.add_argument("--query", help="Barcode or product name to analyse")
    parser.add_argument("--user", default="default", help="User id for preference memory")

    # Preference management.
    parser.add_argument("--set-pref", action="store_true", help="Save preferences for the user")
    parser.add_argument("--diet", choices=["none", "vegetarian", "vegan"])
    parser.add_argument("--low-sugar", action="store_true")
    parser.add_argument("--low-salt", action="store_true")
    parser.add_argument("--allergy", action="append", default=[],
                        help="Allergen to avoid (repeatable), e.g. --allergy peanuts")
    parser.add_argument("--show-prefs", action="store_true", help="Print stored preferences")
    parser.add_argument("--show-log", action="store_true", help="Print recent agent runs")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON result")

    args = parser.parse_args()

    if args.set_pref:
        saved = prefs_module.save_preferences(args.user, {
            "diet": args.diet or "none",
            "low_sugar": args.low_sugar,
            "low_salt": args.low_salt,
            "allergies": args.allergy,
        })
        print(f"Saved preferences for '{args.user}': {saved}")
        return

    if args.show_prefs:
        print(json.dumps(prefs_module.get_preferences(args.user), indent=2))
        return

    if args.show_log:
        for run in read_runs():
            print(json.dumps(run))
        return

    if not args.query:
        parser.error("Provide --query, or use --set-pref / --show-prefs / --show-log")

    result = agent.analyse_product(args.query, user_id=args.user)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_result(result)


if __name__ == "__main__":
    main()
