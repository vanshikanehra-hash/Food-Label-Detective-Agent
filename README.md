# 🕵️ Food Label Detective Agent

An agentic AI assistant that reads packaged-food labels, explains them in plain
English, flags health and dietary concerns, and respects each user's
preferences (vegan, low-sugar, allergy caution) — while keeping the human in
control of the final decision.

> **Capstone Project — Agentic AI Track** · Domain: Consumer safety & nutrition awareness

---

## 1. Problem Statement

Consumers struggle to understand packaged-food labels. Ingredient lists are
long and technical, additive codes (E-numbers) are cryptic, and nutrition
tables are hard to interpret at a glance. Shoppers with allergies or dietary
goals (vegan, low-sugar) have to manually cross-check every product.

**This project builds a working agent** that takes a product (barcode or name),
processes it through a clear workflow, and produces an *actionable* answer:
what the product is, what to watch out for, whether it fits the user's
preferences, and a clear recommendation — plus a reminder that the user decides.

## 2. Dataset / Reference Source

- **Open Food Facts API** — https://openfoodfacts.github.io/openfoodfacts-server/api/
  Used to fetch product ingredients, allergens, nutrition facts, labels, NOVA
  processing group and Nutri-Score.
- **`data/sample_products.csv`** — a small **synthetic starter dataset** (10
  products) with the same columns as the API. It is used as an automatic
  offline fallback so the agent works without a network connection and so the
  test suite is deterministic. It is clearly marked as synthetic.

## 3. Tools Used

- **Python 3** — core language
- **Open Food Facts REST API** — product data (tool/function layer)
- **Claude LLM API** (optional) — plain-English explanation generation
- **SQLite** — user preference memory (long-term memory)
- **Streamlit** — prototype web UI
- **JSONL logging** — auditable trail of agent runs
- **requests, pytest** — HTTP + testing

## 4. Project Workflow

```
User goal/input  ->  Agent understands task  ->  Ask missing questions
      ->  Use tools (Open Food Facts) + memory (SQLite preferences)
      ->  Deterministic analysis (parse, allergens, additives, risk score)
      ->  Apply guardrails (allergy alerts, diet conflicts, disclaimers)
      ->  Produce structured output + plain-English explanation (LLM)
      ->  Log the run for evaluation
```

See [`docs/project_report.md`](docs/project_report.md) for the full architecture
diagrams.

## 5. AI / Agent Component — where the intelligence lives

This is a genuine **agent**, not just an API wrapper. The agentic behaviours:

1. **Task understanding & clarifying questions** — if the user gives no product,
   the agent asks for one instead of failing (`_missing_info_questions`).
2. **Tool use** — it calls the Open Food Facts API (and a CSV fallback tool) to
   retrieve real product data.
3. **Memory** — it remembers each user's diet, sugar/salt goals and allergies in
   SQLite across sessions.
4. **Reasoning / analysis** — a transparent, rule-based engine parses
   ingredients, detects allergens & additives, and computes a 0–100 risk score
   with a fully itemised breakdown.
5. **Guardrails** — allergy alerts, diet-conflict warnings, honest handling of
   missing data, a medical disclaimer, and an explicit human-in-the-loop step.
6. **LLM explanation** — Claude turns the structured analysis into friendly,
   simple English. If no API key is present, a deterministic template writer
   produces the explanation instead, so the project always runs.

> **Why AI here?** The LLM makes technical label data understandable to a
> non-expert, while the deterministic engine keeps safety-critical decisions
> (allergens, risk) auditable and reproducible. AI is used where it adds value —
> explanation and interaction — not for decoration.

## 6. How to Run

```bash
# 1. (Recommended) create a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) enable Claude-generated explanations
export ANTHROPIC_API_KEY="sk-ant-..."
# Without this key the agent still runs using the built-in template writer.

# 4a. Run the web app
streamlit run app/app.py

# 4b. Or use the command line
python -m src.main --set-pref --user alice --diet vegan --low-sugar --allergy milk
python -m src.main --query "Nutella" --user alice
python -m src.main --query 3017620422003 --user alice   # by barcode
python -m src.main --show-log

# 5. Run the validation tests (offline, deterministic)
python -m pytest -v          # or:  python tests/test_agent.py
```

## 7. Demo Screenshots & Video

- 🎬 **Demo video:** [`docs/demo_video.mp4`](docs/demo_video.mp4) — a ~3-minute
  screen recording of the **live Streamlit app** analysing multiple products:
  loading a user's saved preferences, then flagging Nutella (milk allergy), a
  vegan bar (peanut traces), gummy candy (artificial colours), instant noodles
  (MSG, ultra-processed), clean oats, and live Open Food Facts lookups.
- 🖼️ **Presentation:** [`docs/presentation.pptx`](docs/presentation.pptx) (10 slides).
- **Sample output screenshots** (in [`docs/`](docs/)):
  - `screenshot_set_preferences.png` — saving a user's diet/allergy profile
  - `screenshot_result_nutella.png` — a flagged product (allergy + diet + high sugar)
  - `screenshot_result_oats.png` — a clean product for contrast

> Tip: to capture the Streamlit UI too, run `streamlit run app/app.py` and
> screenshot the result card.

## 8. Results & Insights

- 10/10 scenario tests pass (see [`tests/test_agent.py`](tests/test_agent.py)).
- Sample runs are logged in [`logs/sample_agent_runs.jsonl`](logs/sample_agent_runs.jsonl).
  Example outcomes on the demo user (vegan, low-sugar, avoids milk & peanuts):

  | Product | Source | Risk | Recommendation | Why |
  |---|---|---|---|---|
  | Nutella | synthetic | 75/100 (high) | **avoid** | milk allergy + not vegan + high sugar |
  | Rolled Oats | synthetic | 6/100 (low) | ok to consider | clean, vegan, low sugar |
  | Coca-Cola | Open Food Facts (live) | 31/100 (moderate) | ok to consider | high sugar band |
  | Vegan Protein Bar | synthetic | 41/100 (moderate) | **avoid** | may contain peanuts (traces) |
  | Maggi Noodles | Open Food Facts (live) | 65/100 (high) | **avoid** | MSG additive + ultra-processed |

- **Insight:** combining a deterministic risk engine with an LLM explainer gives
  answers that are both *trustworthy* (auditable score) and *understandable*
  (plain English).

## 9. Limitations

- Open Food Facts is crowd-sourced; some products have missing or inaccurate
  fields. The agent flags missing data rather than guessing.
- Allergen and diet detection uses keyword matching — it can miss unusual
  ingredient names or hidden derivatives. **Always read the physical label.**
- The risk score reflects general nutrition guidance (broadly aligned with UK
  FSA front-of-pack thresholds); it is **not** personalised medical advice.
- The LLM explanation depends on the underlying model and requires an API key;
  the offline template writer is simpler in tone.

## 10. Responsible Use

This tool provides **general information from food labels only. It is not
medical or dietary advice.** People with diagnosed allergies or medical
conditions must confirm against the physical package and a qualified
professional. The agent never guarantees a product is "safe" and always keeps
the final eat / don't-eat decision with the human.

## 11. Future Improvements

- OCR: read a photo of a label directly (for products not in the database).
- Barcode scanning from the phone camera in the UI.
- Personalised nutrition thresholds (e.g. diabetic-specific sugar limits).
- A vector store of nutrition guidance for richer, cited explanations.
- Multi-language explanations.

## 12. Team

- Vatsal Jain
- Vidit Jain
- Vanshika Nehra

---

### Repository Structure

```
food_label_detective_agent/
├── data/
│   ├── sample_products.csv      # synthetic starter dataset (offline fallback)
│   └── preferences.db           # SQLite memory (auto-created, git-ignored)
├── notebooks/
│   └── exploration.ipynb        # data exploration + walkthrough
├── src/
│   ├── off_client.py            # Open Food Facts API + CSV fallback (tools)
│   ├── preprocessing.py         # parsing, allergens, additives, risk score
│   ├── preferences.py           # SQLite preference memory
│   ├── guardrails.py            # safety guardrails & recommendation
│   ├── agent.py                 # agent controller (workflow + LLM)
│   ├── logger.py                # JSONL run logging
│   └── main.py                  # command-line interface
├── app/
│   └── app.py                   # Streamlit prototype UI
├── docs/
│   ├── project_report.md        # full report + architecture diagrams
│   └── presentation_outline.md  # 10-slide deck outline
├── tests/
│   └── test_agent.py            # 10 scenario/validation tests
├── logs/
│   └── sample_agent_runs.jsonl  # sample agent step logs
├── requirements.txt
└── README.md
```
