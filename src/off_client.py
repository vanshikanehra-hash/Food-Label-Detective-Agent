"""
Open Food Facts client.

Fetches product data (ingredients, allergens, nutrition, labels) from the
Open Food Facts API. If the network is unavailable, or a barcode is not found,
it falls back to a local synthetic CSV so the agent still works offline.

API docs: https://openfoodfacts.github.io/openfoodfacts-server/api/
"""

from __future__ import annotations

import csv
import os
from typing import Optional

import requests

# Public Open Food Facts product endpoint (v2).
OFF_PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"

# Open Food Facts asks all clients to send a descriptive User-Agent.
HEADERS = {"User-Agent": "FoodLabelDetectiveAgent/1.0 (educational capstone project)"}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SAMPLE_CSV = os.path.join(DATA_DIR, "sample_products.csv")


def _normalise_product(raw: dict) -> dict:
    """Turn a raw Open Food Facts product dict into the fields the agent uses."""
    nutriments = raw.get("nutriments", {}) or {}
    return {
        "source": "openfoodfacts",
        "barcode": str(raw.get("code", "")),
        "product_name": raw.get("product_name") or raw.get("generic_name") or "Unknown product",
        "brands": raw.get("brands", ""),
        "ingredients_text": raw.get("ingredients_text", "") or "",
        "allergens": raw.get("allergens", "") or "",
        "traces": raw.get("traces", "") or "",
        "labels": raw.get("labels", "") or "",
        "categories": raw.get("categories", "") or "",
        # Nutrition per 100 g / 100 ml.
        "energy_kcal_100g": nutriments.get("energy-kcal_100g"),
        "sugars_100g": nutriments.get("sugars_100g"),
        "salt_100g": nutriments.get("salt_100g"),
        "sodium_100g": nutriments.get("sodium_100g"),
        "saturated_fat_100g": nutriments.get("saturated-fat_100g"),
        "fat_100g": nutriments.get("fat_100g"),
        "fiber_100g": nutriments.get("fiber_100g"),
        "proteins_100g": nutriments.get("proteins_100g"),
        "nova_group": raw.get("nova_group"),
        "nutriscore_grade": raw.get("nutriscore_grade", ""),
    }


def _load_sample_rows() -> list[dict]:
    if not os.path.exists(SAMPLE_CSV):
        return []
    with open(SAMPLE_CSV, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _row_to_product(row: dict) -> dict:
    """Convert a synthetic CSV row into the same shape as an API product."""
    def num(key):
        val = row.get(key, "")
        try:
            return float(val) if val not in ("", None) else None
        except (TypeError, ValueError):
            return None

    return {
        "source": "synthetic_csv",
        "barcode": row.get("barcode", ""),
        "product_name": row.get("product_name", "Unknown product"),
        "brands": row.get("brands", ""),
        "ingredients_text": row.get("ingredients_text", ""),
        "allergens": row.get("allergens", ""),
        "traces": row.get("traces", ""),
        "labels": row.get("labels", ""),
        "categories": row.get("categories", ""),
        "energy_kcal_100g": num("energy_kcal_100g"),
        "sugars_100g": num("sugars_100g"),
        "salt_100g": num("salt_100g"),
        "sodium_100g": num("sodium_100g"),
        "saturated_fat_100g": num("saturated_fat_100g"),
        "fat_100g": num("fat_100g"),
        "fiber_100g": num("fiber_100g"),
        "proteins_100g": num("proteins_100g"),
        "nova_group": num("nova_group"),
        "nutriscore_grade": row.get("nutriscore_grade", ""),
    }


def get_product_by_barcode(barcode: str, timeout: int = 8) -> Optional[dict]:
    """
    Look up a product by barcode.

    Order of resolution:
      1. Try the live Open Food Facts API.
      2. Fall back to the local synthetic CSV (offline / not-found case).
    Returns a normalised product dict, or None if nothing matches anywhere.
    """
    barcode = str(barcode).strip()

    # 1) Live API.
    try:
        resp = requests.get(
            OFF_PRODUCT_URL.format(barcode=barcode),
            headers=HEADERS,
            timeout=timeout,
        )
        if resp.status_code == 200:
            payload = resp.json()
            if payload.get("status") == 1 and payload.get("product"):
                return _normalise_product(payload["product"])
    except (requests.RequestException, ValueError):
        # Network error or bad JSON -> silently fall through to the CSV.
        pass

    # 2) Synthetic CSV fallback.
    for row in _load_sample_rows():
        if str(row.get("barcode", "")).strip() == barcode:
            return _row_to_product(row)

    return None


def search_product_by_name(name: str, timeout: int = 8) -> Optional[dict]:
    """
    Search for a product by free-text name. Returns the first good match.

    Falls back to a case-insensitive substring match over the synthetic CSV.
    """
    name = name.strip()
    if not name:
        return None

    # 1) Live search.
    try:
        resp = requests.get(
            OFF_SEARCH_URL,
            headers=HEADERS,
            params={
                "search_terms": name,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 1,
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            products = resp.json().get("products", [])
            if products:
                return _normalise_product(products[0])
    except (requests.RequestException, ValueError):
        pass

    # 2) Synthetic CSV fallback.
    lowered = name.lower()
    for row in _load_sample_rows():
        if lowered in row.get("product_name", "").lower():
            return _row_to_product(row)

    return None


def resolve_product(query: str) -> Optional[dict]:
    """
    Smart entry point: if the query looks like a barcode (all digits, 8-14
    chars) look it up by barcode, otherwise treat it as a product name.
    """
    query = query.strip()
    if query.isdigit() and 8 <= len(query) <= 14:
        return get_product_by_barcode(query)
    return search_product_by_name(query)
