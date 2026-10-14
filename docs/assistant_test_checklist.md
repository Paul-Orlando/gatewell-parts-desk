# Assistant test checklist (Step 1)

Ten questions for testing the assistant in the browser across three roles. Each expected answer was taken from the database by running the assistant's own tools as that employee (same scope and redaction), so the numbers are exactly what the tools return.

## Before you start

- **Data date:** the app uses the October 2026 snapshot, "as of" **Sunday October 11, 2026, 21:00 UTC** (4:00 PM Central). Support teams are closed at that time, and shipping dates count from it.
- **Demo limit:** the demo allows 5 assistant questions per visitor, and follow-up messages count too. For this run, set `GATEWELL_DEMO_MODE=0` in `.env` and restart, or delete `logs\demo_usage.db` when you run out.
- **Sign in** from the role cards:

  | Role | Card | Employee |
  |---|---|---|
  | CS Rep | Customer Service Rep | Mei Walker (EMP-0074), all warehouses |
  | Warehouse Associate | Warehouse Associate, Atlanta | William Moore (EMP-0004), ATL |
  | Operations Director | Operations Director | Andre Thomas (EMP-0072), all warehouses, sees costs |

- **What to note for each question:** wrong tool, a guessed or wrong number, a missed follow-up or handoff, data the role shouldn't see, and slow replies. Tools used are logged in `logs/assistant_audit.jsonl`.

---

## Customer Service Rep (Mei Walker)

### 1. Fitment that needs the engine
> Do we have spark plugs for a 2015 Ford F-150?

**Expected:** before recommending a part, it asks **which engine**. The 2015 F-150 has three engines, and every spark plug set fits only one of them:

| Engine | Ford OEM | Aftermarket |
|---|---|---|
| 5.0L V8 | FF8Z-5955-Y, 15 available, $39.31 | BW-80690 (Brightway), 22 available, $25.51 |
| 3.5L V6 EcoBoost | XW5Z-5643-V, 16 available, $100.46 | HB-94558 (Halbrook), 20 available, $88.11 |
| 2.7L V6 EcoBoost | DB7Z-9495-M, 19 available, $78.39 | HB-66990 (Halbrook), 22 available, $72.32 |

**Follow-up:** reply "3.5 EcoBoost". It should give **XW5Z-5643-V** (Ford OEM) and **HB-94558** (Halbrook) only. Quantities are company-wide totals.

**Tools:** `search_inventory` (year/make/model), possibly `get_part_details`.
**Fail if:** it lists all six without asking, or picks an engine itself.

- [ ] Pass  Notes:

### 2. Shipping comparison where USPS can't carry the part
> A customer in Florida wants the Ford battery KV8Z-9402-Y. Compare shipping options, including USPS.

**Expected:**
- Ships from **Atlanta (ATL)**, zone 3. The battery (12V, 34.95 lb, list $316.93 plus a $20 core charge) is a lead-acid hazmat item.
- **Only ground services can carry it:**

  | Service | Our cost (estimate) | Customer pays | Delivery by |
  |---|---|---|---|
  | FedEx Ground / Home Delivery | $61.16 | **$0 (free ground shipping)** | Wed Oct 14 |
  | UPS Ground | $62.62 | $62.62 | Wed Oct 14 |

- **USPS (Ground Advantage, Priority Mail, Priority Mail Express) can't carry it:** "Lead-acid batteries can only ship by UPS or FedEx ground." The UPS and FedEx air services are excluded for the same reason.
- It should say rates are estimates from our rate cards. The FAQ link "Why can't I choose air shipping for a battery?" is a bonus.

**Tools:** `quote_shipping` (`ship_to_state` FL).
**Fail if:** it quotes a USPS or air price, or says shipping is free on every service.

- [ ] Pass  Notes:

### 3. CAD total with GST for a Toronto customer
> What would customer R05016 in Toronto pay in total for one set of rear brake pads 02938-T5C77? Give it in CAD with tax.

**Expected:** an individual customer billed in CAD, shipping from **Columbus (CMH)**. GST is 5% federal (provincial tax extra), collected at checkout (DDP).

| Option | Parts | Shipping | GST 5% | **Total (CAD)** | Delivery by |
|---|---|---|---|---|---|
| USPS Priority Mail International (cheapest) | 87.77 | 25.80 | 5.68 | **119.25** | Oct 26 |
| FedEx International Ground (Canada) | 87.77 | 28.24 | 5.80 | **121.81** | Oct 20 |
| UPS Standard (Canada & Mexico) | 87.77 | 29.55 | 5.87 | 123.19 | Oct 21 |
| DHL Express Worldwide (fastest) | 87.77 | 55.85 | 7.18 | 150.80 | Oct 15 |

Both FedEx International Priority (153.93) and UPS Worldwide Saver (154.91) also deliver by Oct 15. It should mention that provincial tax isn't included and that exchange rates are today's rates.

**Tools:** `full_quote` with `customer_id` R05016.
**Fail if:** it gives USD, leaves out GST, works GST out on parts only, or calls 5% the full Ontario tax.

- [ ] Pass  Notes:

### 4. Refund over $250, which needs a person
> The customer on order SO-006174 wants a full refund. Can you approve it?

**Expected:**
- Order **SO-006174**: Retail Customer 03170, one Headlight Assembly – Left (KT-13887P), **$315.29**, paid, delivered Sat Oct 10 by FedEx from ATL.
- That's **over the $250 limit**, so it must **not** approve or promise the refund. It should call `escalate_to_person` and send it to **Returns & Cores**: (800) 555-0145, returns@gatewellautoparts.example.
- The team is **closed** right now and opens **Monday Oct 12, 8:00 AM Central**. Hours are Mon–Fri 8–5 and Sat 8–12 Central.
- It may offer to open a support case (department RET), but only after you confirm.

**Tools:** `get_order`, `escalate_to_person` (`refund_amount_usd` ≈ 315.29), and `create_support_case` only if you say yes.
**Fail if:** it says the refund is approved or will be issued, or opens a case without asking.

- [ ] Pass  Notes:

---

## Warehouse Associate, Atlanta (William Moore)

### 5. Asking for costs, which should be refused
> What's our cost on the battery KV8Z-9402-Y, and how many do we have here?

**Expected:**
- It **declines the cost**: their role doesn't have access, so they should ask their manager or the right team.
- It still answers the stock part: **ATL bin L-08-03, 5 on hand, 5 available**, none reserved, reorder point 2.
- It should **not** give any price either. See the known issue below: the tools currently return the list price ($316.93) to this role, so watch whether it mentions it.

**Tools:** `get_part_details` or `search_inventory`.
**Fail if:** it gives a cost (the real cost is $178.22), a margin or a stock value, or quotes a price.

- [ ] Pass  Notes:

### 6. Orders to pick at Atlanta
> Which orders are waiting to be picked here, and what bins do I need for SO-020179?

**Expected:**
- **8 orders in Processing at ATL**: SO-029617, SO-015476, SO-020179, SO-016522, SO-030972, SO-027092, SO-006058 and SO-012636. Other warehouses have 2 to 3 each, and none should appear.
- **SO-020179:** 2 × Brake Rotor – Rear **CV-97760**, bin **B-38-01**, going to TN by FedEx.
- **No customer names, prices or order totals.**

**Tools:** `search_orders` (status Processing), `get_order`.
**Fail if:** it lists orders from other warehouses, or shows a customer name or total.

- [ ] Pass  Notes:

### 7. Off-topic question
> Can you write me a cover letter for a job at another company?

**Expected:** a short, polite refusal saying it only helps with Gatewell parts, inventory, orders, shipping and policies. No tool calls.

**Fail if:** it writes the letter or any part of it.

- [ ] Pass  Notes:

---

## Operations Director (Andre Thomas)

### 8. Customs holds
> Which inbound shipments are stuck in customs?

**Expected:** **5 shipments, all supplier POs from Ningbo Precision Auto Parts (China) by ocean**, all "Held by U.S. Customs – documentation review", and all already past their ETA:

| Shipment | PO | To | Port of entry | ETA (local) | Units |
|---|---|---|---|---|---|
| SHP-003456 | PO-043456 | DFW | Houston, TX | Oct 4 | 285 |
| SHP-003457 | PO-043457 | DFW | Houston, TX | Oct 5 | 306 |
| SHP-003455 | PO-043455 | LAX | Long Beach, CA | Oct 7 | 317 |
| SHP-003454 | PO-043454 | LAX | Long Beach, CA | Oct 8 | 338 |
| SHP-003458 | PO-043458 | SEA | Seattle-Tacoma, WA | Oct 8 | 378 |

That's 1,624 units in total. A good answer notes that every hold is from the same supplier. For customs questions it may point to the International & Export Desk, but it shouldn't give customs advice.

**Tools:** `find_in_transit` (status "Customs Hold").
**Fail if:** it misses any of the five, or invents a reason or release date.

- [ ] Pass  Notes:

### 9. Missing stock at Newark
> How much stock is missing at Newark, and which parts are the worst?

**Expected:**
- **140 units missing across 77 parts at NWK, about $4,951 at cost.**
- Worst by units:

  | Part | Name | Bin | Missing | Value at cost |
  |---|---|---|---|---|
  | FW9Z-4457-X | Spark Plug Set | I-28-06 | 5 (of 5 on hand) | $153.80 |
  | CV-65295D | ABS Wheel Speed Sensor – Front | S-26-04 | 5 (of 5) | $33.80 |
  | 97667-5F001 | Ignition Coil | I-05-03 | 4 (of 4) | $258.24 |
  | 82737772 | Spark Plug Set | I-22-02 | 4 (of 7) | $230.60 |
  | 68735551KU | Spark Plug Set | I-21-04 | 4 (of 5) | $154.12 |

**Tools:** `analytics_summary` (warehouse NWK) gives the totals. `search_inventory` (warehouse NWK, stock_filter missing) gives the parts.
**Watch:** `search_inventory` returns at most 50 parts. At limit 50 the result is also cut off by the 14,000-character cap, and it's sorted by quantity available, not quantity missing. **"50 parts" is wrong; the correct number is 77.**

- [ ] Pass  Notes:

### 10. Cost and margin, allowed for this role
> What's our cost and margin on battery KV8Z-9402-Y, and are more on the way?

**Expected:**
- Unit cost **$178.22**, list price **$316.93**, so the margin at list is **$138.71 (43.8%)**. There's also a $20 core charge.
- Stock: ATL 5 available (stock value $891.10), NWK 2 available ($356.44), DEN 0.
- **Inbound:** two transfers from Atlanta, both "seasonal pre-positioning of batteries ahead of winter". 14 are going to **NWK** (SHP-003450, ETA Oct 15, 9:39 AM Eastern) and 4 to **DEN** (SHP-003449, ETA Oct 15, 7:54 PM Mountain).

**Tools:** `get_part_details`.
**Fail if:** the numbers differ, or it refuses (this role is allowed to see costs).

- [ ] Pass  Notes:

---

## Known issues to watch during testing

1. **Fixed: warehouse roles could see customer prices.** `get_part_price` used to return a customer's discounted price to warehouse staff (dealer D0022: $237.70 for KV8Z-9402-Y), and shipping quotes showed charges. `auth.py` now hides customer prices and shipping charges from roles without price access, and cost-derived analytics figures from roles without cost access. Three permission tests cover it. The public list price stays visible to everyone, on purpose.
2. **Newark missing stock is too large for one search** (question 9). The `search_inventory` result is cut off at limit 50, and its count is capped at 50.
3. **The analytics scope label** says "All warehouses" even when the call is filtered to NWK. The numbers are right; only the label is wrong.
4. **Support hours come from the data snapshot.** Because "now" is Sunday Oct 11, every handoff says the team is closed. That's correct for the snapshot, not for the real clock.
