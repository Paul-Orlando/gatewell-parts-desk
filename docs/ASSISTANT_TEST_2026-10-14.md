# Assistant live test: 2026-10-14

- **Model:** Gemini 3.1 Flash-Lite via OpenRouter (`google/gemini-3.1-flash-lite`)
- **App:** running locally at http://localhost:8000, demo mode on (5 questions per visitor)
- **Method:** each question sent to `POST /api/chat` as the named employee, one question per conversation. The reply, the tools used, and the time were recorded. Expected answers were checked against the database through the app's own API.

## Summary

| # | Role (employee) | Question | Result | Time |
|---|---|---|---|---|
| 1 | Customer Service Rep (EMP-0074) | Do we have front brake pads for a 2019 Honda Civic in stock? | PASS | 2.5 s |
| 2 | Customer Service Rep (EMP-0074) | Compare UPS, FedEx and USPS to ship a front bumper cover for a 2020 Toyota Camry to Dallas, Texas, home address. | PASS, one issue | 3.8 s |
| 3 | Customer Service Rep (EMP-0074) | A customer received the wrong radiator and wants a $400 refund. They're upset and want to talk to someone. | PASS, two issues | 3.0 s |
| 4 | Warehouse Associate, Atlanta (EMP-0004) | What's our unit cost and margin on part 68253600AW, and which customers ordered it? | PASS, one issue | 2.1 s |
| 5 | Operations Director (EMP-0072) | Which warehouse has the most missing stock, which categories, and what's it worth at cost? | **FAIL** | 10.7 s |
| 6 | Operations Director (EMP-0072) | (6th question, to test the demo limit) | PASS: HTTP 429 with the limit message | — |

**Overall:** fast (2–4 s), correct tool choice, exact numbers, correct handoffs and role limits. The one failure comes from tool definitions that don't tell the model the valid warehouse codes or analytics sections, not from the model itself.

## Details

### 1. Civic front brake pads: PASS

- **Tools:** `search_inventory {"year":2019,"make":"Honda","model":"Civic","q":"front brake pads"}`
- **Reply (summary):** three options in stock:
  - 38080-TGH-Y22, Honda OEM: 17 available, $88.91
  - KT-14449, Kessler Teknik (Premium): 13 available, $76.54
  - TY-82726, Taeyang Parts (Value): 6 available, $54.34

  It offered to check a warehouse or quote shipping.
- **Verified:** all three parts, quantities and prices match `/api/inventory` exactly.

### 2. Bumper cover shipping comparison: PASS, one issue

- **Tools:**
  1. `search_inventory {"make":"Toyota","model":"Camry","q":"front bumper cover","year":2020}`
  2. `quote_shipping {"ship_to_country":"US","ship_to_state":"TX","residential":true,"items":[{"part_number":"KT-05409","quantity":1}]}`
- **Reply (summary):** quoted KT-05409 from Atlanta, from FedEx Ground at $211.54 up to UPS Next Day Air at $384.94. It said USPS can't ship the item because of its size, labeled the rates as estimates, and said oversize parts aren't eligible for free shipping.
- **Issue A:** two bumper covers match: KT-05409, Kessler Teknik Premium (2 available), and 44506-3K857, Toyota OEM (1 available). The assistant quoted the Premium part without mentioning the OEM option or asking which one.

### 3. $400 refund, customer wants a person: PASS, two issues

- **Tools:** `escalate_to_person {"question":"Customer received wrong radiator and is requesting a $400 refund. They are upset and want to speak with someone.","refund_amount_usd":400,"reason":"Refund request exceeds $250 limit and customer is upset."}`
- **Handoff (correct):**
  - Routed to Returns & Cores (RET), currently closed, reopening Monday Oct 12, 8:00 AM (America/Chicago).
  - Gave the phone (800) 555-0145 and email returns@gatewellautoparts.example.
  - FAQ links: "I received the wrong part." and "What is your return policy?"
- **Issue B:** the reply says *"I have provided the customer with the following information"* and *"Our team will follow up with them."* The assistant talks to employees and didn't contact the customer, so this is inaccurate. It should say "You can tell the customer…".
- **Issue C:** it didn't offer to open a support case, though customer service roles can have it do that.

### 4. Warehouse associate asks for costs and customers: PASS, one issue

- **Tools:** `get_part_details {"part_number":"68253600AW"}`. The result was already redacted for the warehouse role.
- **Reply:** correctly said the role can't see unit cost, margin or customer names, and suggested asking a manager.
- **Issue D:** it didn't offer what the associate *can* see. This part is the planted Atlanta backorder: 0 available at ATL, 11 backordered, 120 arriving on an expedited air shipment.

### 5. Missing stock by warehouse: FAIL

- **Reply:** "I couldn't finish looking that up. Try a narrower question, or contact Customer Service at (800) 555-0142." It hit the 8-round limit.
- **Tools called (8):**
  1. `analytics_summary {"sections":["kpis"]}`
  2. `search_inventory {"stock_filter":"missing"}`
  3. `analytics_summary {"warehouse":"ATL","sections":["kpis"]}`
  4. `analytics_summary {"sections":["kpis"],"warehouse":"CHI"}` ← not a real code (should be ORD)
  5. `analytics_summary {"warehouse":"DAL","sections":["kpis"]}` ← not a real code (should be DFW)
  6. `analytics_summary {"sections":["kpis"],"warehouse":"DEN"}`
  7. `analytics_summary {"warehouse":"LAX","sections":["kpis"]}`
  8. `analytics_summary {"sections":["kpis"],"warehouse":"MIA"}` ← not a real code; there is no Miami warehouse
- **Expected answer** (from `/api/analytics?period=all`): **Newark (NWK), 140 units missing**, far ahead of Atlanta (12) and Inland Empire/LAX (10). The top categories are Sensors (89 units, $3,014 at cost), Ignition (51 units, $1,848) and Brakes (16 units, $946). The company-wide total is $8,388 at cost.
- **Causes:**
  - **E. Warehouse codes aren't given to the model.** It guessed CHI, DAL and MIA. The server silently accepted them and returned empty results instead of an error.
  - **F. Analytics section names aren't given to the model.** It only asked for `kpis`, which has the company total but no breakdown. The data it needed was in `inventory_by_warehouse` and `missing_by_group`, but the schema doesn't list the sections. Also, `inventory_by_warehouse` has missing units but no missing value in dollars.
  - **G. One lookup per round:** it called tools one at a time, so 8 calls used up all 8 rounds.
- **Issue H:** the failed reply still used up one of the visitor's 5 demo questions.

## Fixes requested

1. **Warehouse codes (E):** make `warehouse` an enum of the 11 real codes in every tool schema that has it (`search_inventory`, `find_in_transit`, `search_orders`, `analytics_summary`). List the codes with their cities in the system prompt. Reject unknown codes on the server with an error that lists the valid ones.
2. **Analytics sections (F):** make `analytics_summary.sections` an enum of the real section names from `analytics.dashboard()`, each with a one-line description. Add `missing_value_usd` per warehouse to `inventory_by_warehouse`.
3. **System prompt (B, C, A, D, G):** add these rules.
   - You are talking to an employee; never claim to have contacted, told or sent anything to a customer. Say "you can tell the customer…".
   - After a handoff, offer customer service roles "Want me to open a support case?"
   - When several parts match (OEM, Premium, Value), mention the options before quoting one, or ask which one.
   - When refusing restricted data, offer what the employee can see.
   - Prefer one broad lookup (for example, an analytics section covering all warehouses) over many narrow ones.
4. **Demo limit (H):** a "couldn't finish" reply doesn't count against the visitor's questions.
5. **Tests:** add a test for each fix, then run the full suite.

## Retest after fixes

Run with `GATEWELL_DEMO_MODE=0`:

- **Questions 1–5 above.** Question 5 must return Newark (NWK), 140 units, mostly Sensors and Ignition, with values.
- **CS Rep:** "A customer in Toronto wants 2 front struts for a 2018 F-150. What's the total in CAD with shipping?" Expect a CAD total that includes 5% GST, per carrier.
- **Any role:** "What's the weather in Atlanta?" Expect a polite decline, since it's off-topic.
- **Operations Director:** "What's held in customs right now?" Expect 5 Ningbo shipments, past their ETA.
