# Food Label Detective Agent — Project Report

**Track:** Agentic AI (AAI) · **Difficulty:** Basic + Intermediate
**Domain:** Consumer safety and nutrition awareness

---

## 1. Problem Understanding & Stakeholders

### The problem
Packaged-food labels are hard for ordinary shoppers to interpret. Ingredient
lists use technical names, additives appear as cryptic E-numbers, and nutrition
tables require mental arithmetic to judge. People with **allergies** or dietary
goals (**vegan, vegetarian, low-sugar, low-salt**) must manually check every
product, which is slow and error-prone.

### Users / stakeholders
- **Primary user:** an everyday grocery shopper who wants a quick, plain-English
  read on a product and a warning if it clashes with their needs.
- **Secondary:** parents managing a child's allergy; people with lifestyle diet
  goals; carers.
- **Why "human-in-the-loop" matters:** food/allergy decisions are sensitive. The
  agent *informs*; the human *decides*.

### Inputs, outputs, success criteria
| Aspect | Definition |
|---|---|
| **Input** | A product barcode or name + the user's stored preferences |
| **Output** | Plain-English explanation, allergen/diet flags, 0–100 risk score, recommendation, logs |
| **Success** | Correct allergen/diet detection, transparent risk score, clear guardrails, works online *and* offline |

---

## 2. Data / Reference Material

- **Open Food Facts API** (primary): live product ingredients, allergens,
  nutrition (per 100 g), labels, NOVA processing group, Nutri-Score.
- **`data/sample_products.csv`** (synthetic fallback): 10 hand-authored products
  with the same schema, used when the API is unreachable or a code is missing,
  and to keep tests deterministic. Explicitly synthetic starter data.

Key fields used: `ingredients_text`, `allergens`, `traces`, `labels`,
`sugars_100g`, `salt_100g`, `saturated_fat_100g`, `fat_100g`, `nova_group`,
`nutriscore_grade`.

---

## 3. System / Pipeline Architecture

```
┌──────────────┐     ┌──────────────────┐
│ User Interface│────▶│  Agent Controller │
│ (Streamlit/CLI)│    │    (agent.py)     │
└──────────────┘     └───────┬──────────┘
                             │ orchestrates
        ┌────────────────────┼─────────────────────┐
        ▼                    ▼                     ▼
 ┌─────────────┐     ┌───────────────┐     ┌───────────────┐
 │ Tools/APIs  │     │ Memory / KB   │     │ Prompt Workflow│
 │ off_client  │     │ preferences   │     │  (LLM system   │
 │ (OFF + CSV) │     │  (SQLite)     │     │   prompt)      │
 └──────┬──────┘     └──────┬────────┘     └───────┬───────┘
        └──────────┬────────┴──────────────────────┘
                   ▼
          ┌─────────────────┐     ┌────────────────┐
          │ Analysis engine  │────▶│ Guardrail Check │
          │ (preprocessing)  │     │ (guardrails.py) │
          └─────────────────┘     └───────┬────────┘
                                          ▼
                             ┌──────────────────────────┐
                             │ Final Answer + JSONL Logs │
                             └──────────────────────────┘
```

### Agent workflow (step by step)
1. **Understand task** — read the query and user id.
2. **Ask missing questions** — if no product is given, request one.
3. **Use tools + memory** — fetch product (API → CSV fallback); load preferences.
4. **Analyse** — parse ingredients, detect allergens & additives, score risk.
5. **Apply guardrails** — allergy/diet conflicts, data-quality notes, disclaimer.
6. **Explain** — LLM (Claude) writes plain English; template writer if no key.
7. **Log** — append a structured record to `logs/agent_runs.jsonl`.

---

## 4. Core Modules

| Module | Responsibility |
|---|---|
| `src/off_client.py` | Tool layer: Open Food Facts API + synthetic-CSV fallback |
| `src/preprocessing.py` | Ingredient parsing, allergen/additive detection, nutrition assessment, transparent risk score |
| `src/preferences.py` | SQLite long-term memory of user diet/allergies |
| `src/guardrails.py` | Safety layer: conflict detection, recommendation, disclaimers, human-in-the-loop |
| `src/agent.py` | Controller tying the workflow together + LLM/template explanation |
| `src/logger.py` | JSONL logging of every run |
| `src/main.py` | CLI |
| `app/app.py` | Streamlit UI |

### Risk score design (transparent & auditable)
Points are added and *recorded* for: high/moderate nutrients (sugar, salt,
saturated fat, total fat), notable additives, NOVA ultra-processing, and poor
Nutri-Score. Score is capped at 100 and banded low (<30) / moderate (30–59) /
high (≥60). Every point is shown in the "Why this risk score?" breakdown, so the
number is never a black box.

---

## 5. AI / Agent Component

- **LLM (Claude)** converts structured analysis into shopper-friendly English via
  a carefully scoped system prompt that forbids medical advice and hallucinated
  facts. Model defaults to `claude-sonnet-5` (override with `LLM_MODEL`).
- **Deterministic fallback** guarantees the project runs with no API key.
- **Agentic properties:** clarifying questions, tool use, persistent memory,
  reasoning, guardrails — the six core agent modules required by the brief.

---

## 6. Validation & Evaluation

- **10 scenario tests** in `tests/test_agent.py` cover ingredient parsing,
  allergen detection, vegan/non-vegan classification, high-sugar risk, the
  allergy guardrail, additive detection, the full end-to-end workflow, the
  not-found path, and the clarifying-question path. **Result: 10/10 pass.**
- **Sample run log** (`logs/sample_agent_runs.jsonl`) demonstrates real outputs
  on 5 products (mix of live-API and synthetic), showing correct risk bands and
  recommendations for a vegan, low-sugar, milk/peanut-avoiding user.

### Evaluation summary
| Metric | Result |
|---|---|
| Scenario tests passing | 10 / 10 |
| Allergy alert precision (sample set) | Correctly fired on all milk/peanut products |
| Works offline | Yes (CSV fallback + template explainer) |
| Works with live API | Yes (verified on Coca-Cola, Maggi) |

---

## 7. Guardrails & Responsible Use

- **Allergy alerts** are surfaced first and marked *critical*.
- **No medical advice**: a standing disclaimer accompanies every result.
- **Honest about missing data**: the agent notes when ingredients or nutrition
  are unavailable instead of guessing.
- **Human-in-the-loop**: the final decision is always handed back to the user.

---

## 8. Limitations

See README §9. In short: crowd-sourced data gaps, keyword-based detection,
general (not personalised) nutrition thresholds, and LLM dependence for the
richest explanations.

---

## 9. Future Improvements

OCR of label photos, in-app barcode scanning, personalised thresholds, a vector
store of cited nutrition guidance, and multi-language output.

---

## 10. Conclusion

The Food Label Detective Agent delivers a complete, working agentic workflow —
from input, through tool use and memory, to guardrailed, explained output with
logging. It pairs an auditable rule-based safety engine with an LLM explainer,
demonstrating responsible AI in a sensitive consumer domain while keeping humans
in control.
