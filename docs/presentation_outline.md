# Presentation Outline — Food Label Detective Agent

Prepare 8–10 slides (export to `presentation.pdf` for submission).

---

**Slide 1 — Title & Team**
- Food Label Detective Agent 🕵️
- Track: Agentic AI · Domain: Consumer safety & nutrition
- Team member name(s)

**Slide 2 — Problem & Real-World Impact**
- Food labels are hard to read; additives are cryptic; allergy/diet checks are manual.
- Impact: a practical assistant that helps everyday shoppers decide safely — human stays in control.

**Slide 3 — Dataset / Reference Source**
- Open Food Facts API (live product data: ingredients, allergens, nutrition, NOVA, Nutri-Score).
- Synthetic starter CSV (10 products) as offline fallback + for deterministic tests.

**Slide 4 — System Workflow**
- Diagram: Input → Understand → Ask if missing → Tools + Memory → Analyse → Guardrails → Explain → Log.
- Show the architecture diagram from the report.

**Slide 5 — AI / Agent Innovation**
- 6 agent modules: clarifying questions, tool use, SQLite memory, reasoning, guardrails, LLM explanation.
- Transparent rule-based risk score + Claude plain-English explainer (offline template fallback).
- "AI where it adds value, not decoration."

**Slide 6 — Prototype / Demo Screenshots**
- Streamlit UI: preferences sidebar, product input, result card with allergy alert.

**Slide 7 — Results / Sample Outputs**
- Table: Nutella (avoid), Oats (ok), Coca-Cola (moderate), Vegan Bar (avoid – peanut traces), Maggi (avoid).
- 10/10 scenario tests pass; sample run log.

**Slide 8 — Limitations & Responsible Use**
- Crowd-sourced data gaps; keyword detection; not medical advice; always read the physical label.
- Human-in-the-loop; standing disclaimer.

**Slide 9 — Future Improvements**
- OCR of label photos, in-app barcode scan, personalised thresholds, cited RAG guidance, multi-language.

**Slide 10 — Conclusion**
- A complete, responsible agentic workflow: trustworthy (auditable score) + understandable (plain English).

---

## Demo Video Script (5–8 minutes)

1. **(0:00–0:45) Problem & users** — show a confusing real food label; explain who benefits.
2. **(0:45–1:30) Data** — open the Open Food Facts page + the synthetic CSV; explain the fallback.
3. **(1:30–3:00) System walk-through** — open the code: `agent.py` workflow, `preprocessing.py` risk score, `guardrails.py`.
4. **(3:00–5:00) Live demo** — in Streamlit: set preferences (vegan, low-sugar, avoid milk/peanuts), analyse "Nutella" → show the critical allergy alert + risk breakdown; then analyse "Rolled Oats" → clean result; then a live-API product by barcode.
5. **(5:00–6:00) Where AI is used** — point out the LLM explanation vs template fallback, and the memory/guardrails.
6. **(6:00–7:00) Sample output + tests** — run `python tests/test_agent.py` (10/10), show `--show-log`.
7. **(7:00–8:00) Limitations & responsible use** — read the disclaimer; stress human-in-the-loop; future work.
