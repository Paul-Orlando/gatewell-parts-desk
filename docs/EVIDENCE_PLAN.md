# Evidence plan: recommendations, evaluation, user test, demo

Goal: show that the app helps employees make decisions faster, and back that up with measured results. Work in four phases, **one phase per Claude Code conversation**, in this order. Each phase follows CLAUDE.md: plan mode first, tests, and a commit at the end.

---

## Phase A: Decision support (read-only recommendations)

The app suggests actions; people decide. Nothing is created or changed.

### A1. Service: `app/recommend.py`

`recommend_for_part(emp, part_number, warehouse=None)` returns, for one part at one warehouse (the employee's own warehouse when they have one):

1. **Transfer options:** other warehouses whose available stock is above their own reorder point. For each:
   - quantity they can spare (available minus reorder point; never below 0)
   - estimated ground shipping cost and transit days, from the existing rate engine (`quote_shipping` with `from_warehouse`, warehouse to warehouse, non-residential)
   - sort by days, then cost
2. **Reorder recommendation:** suggested quantity = reorder_qty minus units already in transit (never below 0). Include the primary supplier, its country, and the typical lead time: about 30 days for Japan, Korea, China and Germany; about 8 days for Mexico, Canada and the U.S. If inbound stock already covers the shortfall, say so and recommend no reorder.
3. **Substitute parts:** in-stock equivalents from `part_interchange`, with quality tier, price and available quantity at that warehouse.
4. **Summary line in plain English,** for example: "Atlanta is out (11 backordered). 120 arrive Oct 14 by air. Fastest cover: transfer 6 from Dallas (2 days, about $X)."

`recommend_for_warehouse(emp, warehouse, category=None, limit=15)` returns the same summary for the top low-stock parts, ordered with backorders first.

**Rules:**
- **Role scope:** an employee only gets recommendations *for* warehouses in their scope, but may see stock *at* any warehouse as a transfer source.
- **Redaction:** shipping cost estimates are cost data, so redact them for roles that can't see costs (warehouse staff and customer service). They still see days and quantities.
- **Read-only:** never write to the database; label every output as a suggestion.

### A2. Assistant tool: `recommend_actions`

- **Who gets it:** managers, customer service supervisors and customer service reps. Warehouse staff get the transfer and substitute parts but not reorder; or, if it's simpler, the same tool with the reorder section removed by role.
- **Inputs:** `part_number` (optional), `warehouse` (enum of the 11 codes), `category` (enum of the category groups).
- **System prompt rule:** "When stock is low, out or backordered, call recommend_actions and present the options as suggestions for a person to decide on. Never say an action has been taken."

### A3. Interface

- **Part drawer:** add a **"Suggested actions"** section under "Stock by warehouse". It shows the summary line, then small tables for transfer options, the reorder recommendation and substitutes. Include a note: "Suggestions only. Nothing is ordered or moved."
- **Analytics → Low stock to reorder:** add a "Suggested action" column with a short text, for example "Transfer 6 from DFW" or "Covered by inbound 120" or "Reorder 40". Clicking the part opens the drawer, as now.
- Follow the Interface design rules in CLAUDE.md.

### A4. Tests

- the Atlanta backorder part (IH-100009) gets the inbound shipment noted, and no reorder if inbound covers it
- transfer sources never suggest a warehouse taking itself below its reorder point
- scope: an Atlanta manager can't get recommendations for Newark
- redaction: a CS rep doesn't see shipping cost in recommendations
- the database is unchanged after calls (row counts before and after)
- the assistant tool is offered to the right roles only

---

## Phase B: Evaluation set and runner

### B1. Questions: `tests/eval/questions.yaml`

50 questions in 7 groups:
- stock and fitment (10)
- orders (6)
- shipping and quotes (8)
- international and currency (6)
- analytics and recommendations (6)
- restricted data across roles (8)
- handoffs and off-topic (6)

Start with the 9 from `docs/ASSISTANT_TEST_2026-10-14.md` and `docs/ASSISTANT_RETEST_2026-10-14.md`.

Each question has:
- `id`, `group`, `employee_id`, `question`
- `expect_facts`: strings or numbers that must appear in the answer. Take them from the database, never guess.
- `forbid`: strings that must NOT appear (for example a unit cost for a warehouse role, a tool name, a fake warehouse code)
- `expect_tools`: at least one of these must be called
- `expect_handoff`: true or false, and the department when true
- `expect_refusal`: true or false

### B2. Runner: `tests/eval/run_eval.py`

This calls the real model, so keep it out of the normal pytest run.

- Runs every question **3 times** through `assistant.chat()`, as that employee, with the demo limit off.
- Scores each run: facts present, nothing forbidden, right tool, correct handoff or refusal. Each is pass/fail; a question passes when all four pass in a run.
- Records the time, the token counts from the audit log, and the estimated cost. Use $0.25 per 1M input and $1.50 per 1M output tokens for Gemini 3.1 Flash-Lite, configurable per model.
- Accepts `--model`, so the same set can run on a second model.
- Outputs:
  - `tests/eval/results/<date>_<model>.csv`, one row per run
  - `tests/eval/results/<date>_<model>.md`: pass rate overall and by group; consistency (questions that passed all 3 runs); refusal accuracy; average and 95th-percentile time; average cost per question; and a list of failures with the answer given
- Runs on Windows as `.venv\Scripts\python tests\eval\run_eval.py`.

### B3. Comparison

After running Flash-Lite, run one other model, chosen by me, and write `tests/eval/results/COMPARISON.md` with a side-by-side table.

---

## Phase C: User test kit (documents only, no code)

Create `docs/user_test/`:

1. **`script.md`:** a 20-minute session.
   - a short intro: they're testing the app, not being tested. Include the line "Vehicles and carriers are fictional equivalents of common U.S. models and major parcel carriers."
   - one consent line
   - five timed tasks, each done twice: first with the screens only, then with the assistant
     1. Is there a front brake pad for a 2019 Ferra Motors Nivo in stock near Atlanta?
     2. What's the cheapest way to ship a front bumper cover for a 2020 Aravel to Dallas, and when would it arrive?
     3. As a warehouse associate in Atlanta: where is part IH-100009 shelved, and when is more arriving?
     4. As the Operations Director: which warehouse is losing stock, in which category, and which part should we look at first?
     5. A customer wants a $400 refund for a wrong radiator. What do you do?
   - three closing questions: what was confusing; what would you use daily; a 1–5 rating
2. **`results_template.csv`:** participant, background, task, method (screens or assistant), seconds, success, notes.
3. **`summary_template.md`:** a before/after table (median time and success for each task and method), quotes, and "changes we made because of feedback".

---

## Phase D: Demo preparation

1. **`docs/DEMO_SCRIPT.md`:** a five-minute script with exact clicks and questions, one role per beat:
   - **0:00:** the role cards. Opening narration, said aloud while the role cards are on screen: "Vehicles and carriers are fictional equivalents of common U.S. models and major parcel carriers."
   - **0:30:** CS Rep asks for the Toronto struts total in CAD.
   - **1:30:** CS Rep asks about the $400 refund.
   - **2:15:** the Warehouse Associate asks for costs on IH-100009.
   - **3:00:** the Operations Director goes Analytics → Newark → Sensors → clicks the part → Suggested actions.
   - **4:15:** the evidence slide (eval pass rate, user test result, cost per question).

   Include the expected answer for each step, and a fallback if the model is slow.
2. **Weekday demo time:** add a documented setting so the demo can run as Monday 10:00 AM Central (`GATEWELL_AS_OF=2026-10-12T15:00:00Z`), so at least one handoff shows the team as open. Replace the hard-coded `'2026-10-11T21:00:00'` in the `v_stock_position` view's days-since-activity calculation with the app's as-of time, so stock age stays consistent. Make sure all tests still pass with both settings.
3. **`docs/DEMO_CHECKLIST.md`:**
   - before the demo: restart with demo mode off, reset the demo counter, check the OpenRouter key and credit, open the role cards page
   - record a backup video
