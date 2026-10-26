"""
Streamlit UI for the Food Label Detective Agent.

Run from the project root:
    streamlit run app/app.py
"""

from __future__ import annotations

import os
import sys

import streamlit as st

# Make `src` importable when Streamlit runs this file directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import agent  # noqa: E402
from src import preferences as prefs_module  # noqa: E402

st.set_page_config(page_title="Food Label Detective", page_icon="🕵️", layout="centered")

RECOMMENDATION_STYLE = {
    "avoid": ("🚫 Best avoided", "#b00020"),
    "caution": ("⚠️ Use caution", "#b8860b"),
    "ok_to_consider": ("✅ Looks reasonable", "#1b7f3b"),
}

# ---------------------------------------------------------------- sidebar ---
st.sidebar.header("👤 Your preferences")
user_id = st.sidebar.text_input("User name", value="default")

stored = prefs_module.get_preferences(user_id)
diet = st.sidebar.selectbox(
    "Diet", ["none", "vegetarian", "vegan"],
    index=["none", "vegetarian", "vegan"].index(stored["diet"]),
)
low_sugar = st.sidebar.checkbox("Trying to cut down on sugar", value=stored["low_sugar"])
low_salt = st.sidebar.checkbox("Watching salt intake", value=stored["low_salt"])
allergy_options = ["milk", "eggs", "peanuts", "tree nuts", "soy", "gluten",
                   "fish", "shellfish", "sesame"]
allergies = st.sidebar.multiselect("Allergies to avoid", allergy_options,
                                    default=stored["allergies"])

if st.sidebar.button("💾 Save preferences"):
    prefs_module.save_preferences(user_id, {
        "diet": diet, "low_sugar": low_sugar,
        "low_salt": low_salt, "allergies": allergies,
    })
    st.sidebar.success("Preferences saved. The agent will remember them.")

llm_on = bool(os.environ.get("ANTHROPIC_API_KEY"))
st.sidebar.caption(
    ("🧠 LLM explanations: ON (Claude)" if llm_on
     else "🧠 LLM explanations: OFF — using built-in template writer.\n"
          "Set ANTHROPIC_API_KEY to enable Claude.")
)

# ------------------------------------------------------------------ main ---
st.title("🕵️ Food Label Detective Agent")
st.write(
    "Enter a **barcode** or **product name**. The agent reads the label, "
    "explains it in plain English, and flags anything that clashes with your "
    "preferences. It keeps *you* in control of the final decision."
)

query = st.text_input("Product barcode or name",
                      placeholder="e.g. 3017620422003  or  Nutella")

if st.button("🔍 Analyse label", type="primary") and query:
    # Persist the sidebar preferences for this run.
    prefs_module.save_preferences(user_id, {
        "diet": diet, "low_sugar": low_sugar,
        "low_salt": low_salt, "allergies": allergies,
    })

    with st.spinner("Reading the label..."):
        result = agent.analyse_product(query, user_id=user_id)

    if result["status"] == "needs_input":
        for q in result["questions"]:
            st.warning(q)
    elif result["status"] == "not_found":
        st.error(result["message"])
    else:
        product = result["product"]
        analysis = result["analysis"]
        guard = result["guardrails"]

        label, colour = RECOMMENDATION_STYLE[guard["recommendation"]]
        st.markdown(
            f"### {product['product_name']}  \n"
            f"<span style='color:{colour};font-size:1.3rem;font-weight:700'>{label}</span> "
            f"&nbsp;·&nbsp; Risk score **{analysis['risk']['score']}/100** "
            f"({analysis['risk']['band']})",
            unsafe_allow_html=True,
        )
        st.caption(f"Data source: {product['source']} · "
                   f"Explanation by: {result['explanation_source']}")

        # Critical allergy alerts first, loud and clear.
        for c in guard["conflicts"]:
            if c["severity"] == "critical":
                st.error(c["message"])
            elif c["severity"] == "warning":
                st.warning(c["message"])

        st.subheader("Plain-English explanation")
        st.write(result["explanation"])

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Nutrition (per 100g)")
            if analysis["nutrition"]:
                for n in analysis["nutrition"]:
                    icon = {"high": "🔴", "moderate": "🟠", "low": "🟢"}[n["level"]]
                    st.write(f"{icon} {n['message']}")
            else:
                st.write("No nutrition data available.")

            st.subheader("Allergens")
            st.write(", ".join(analysis["allergens"]) if analysis["allergens"]
                     else "None detected in available data.")

        with col2:
            st.subheader("Additives")
            if analysis["additives"]:
                for a in analysis["additives"]:
                    st.write(f"• {a}")
            else:
                st.write("None of note.")

            st.subheader("Diet")
            d = analysis["dietary"]
            st.write(f"Vegan: {'✅' if d['vegan'] else '❌'}  ·  "
                     f"Vegetarian: {'✅' if d['vegetarian'] else '❌'}")

        with st.expander("🔎 Why this risk score? (transparent breakdown)"):
            for reason in analysis["risk"]["reasons"] or ["No risk factors detected."]:
                st.write(f"- {reason}")

        if guard["data_notes"]:
            with st.expander("ℹ️ Data quality notes"):
                for note in guard["data_notes"]:
                    st.write(f"- {note['message']}")

        st.divider()
        st.info(guard["human_in_the_loop"])
        st.caption(guard["disclaimer"])

st.divider()
st.caption(
    "Educational capstone project · Data from Open Food Facts · "
    "Not medical advice."
)
