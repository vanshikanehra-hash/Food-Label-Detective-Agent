"""
User preference memory (SQLite).

Stores each user's dietary preferences so the agent "remembers" them across
sessions: diet type (vegan / vegetarian / none), low-sugar goal, and a list of
allergens to avoid. This is the agent's long-term memory component.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "preferences.db")

DEFAULT_PREFERENCES = {
    "diet": "none",          # one of: none | vegetarian | vegan
    "low_sugar": False,      # user is trying to cut down on sugar
    "low_salt": False,       # user is watching salt intake
    "allergies": [],         # list of allergen families to avoid, e.g. ["peanuts"]
}


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS preferences (
            user_id     TEXT PRIMARY KEY,
            diet        TEXT NOT NULL DEFAULT 'none',
            low_sugar   INTEGER NOT NULL DEFAULT 0,
            low_salt    INTEGER NOT NULL DEFAULT 0,
            allergies   TEXT NOT NULL DEFAULT '[]',
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def get_preferences(user_id: str) -> dict:
    """Load a user's stored preferences, or sensible defaults if none exist."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT diet, low_sugar, low_salt, allergies FROM preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return dict(DEFAULT_PREFERENCES)

    diet, low_sugar, low_salt, allergies = row
    try:
        allergies_list = json.loads(allergies)
    except (TypeError, ValueError):
        allergies_list = []
    return {
        "diet": diet,
        "low_sugar": bool(low_sugar),
        "low_salt": bool(low_salt),
        "allergies": allergies_list,
    }


def save_preferences(user_id: str, preferences: dict) -> dict:
    """Insert or update a user's preferences and return the stored version."""
    merged = dict(DEFAULT_PREFERENCES)
    merged.update({k: v for k, v in preferences.items() if k in DEFAULT_PREFERENCES})

    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO preferences (user_id, diet, low_sugar, low_salt, allergies, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                diet=excluded.diet,
                low_sugar=excluded.low_sugar,
                low_salt=excluded.low_salt,
                allergies=excluded.allergies,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                user_id,
                merged["diet"],
                int(bool(merged["low_sugar"])),
                int(bool(merged["low_salt"])),
                json.dumps(merged["allergies"]),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return merged


def reset_preferences(user_id: str) -> None:
    """Delete a user's stored preferences."""
    conn = _connect()
    try:
        conn.execute("DELETE FROM preferences WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
