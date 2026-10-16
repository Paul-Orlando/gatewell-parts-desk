# Assistant evaluation: google/gemini-3.1-flash-lite

Run on Fri, Oct 16, 2026. 50 questions × 3 run(s) = 150 runs, 9.0 minutes.

Re-scored from 2026-10-16_google-gemini-3.1-flash-lite_after.csv with today's questions.yaml (no model calls). Time, tool calls and cost are from the original run. Handoff departments were inferred from the original checks.

| Measure | Result |
|---|---|
| Pass rate (all runs) | 144/150 (96%) |
| Consistency (questions that passed every run) | 47/50 (94%) |
| Refusal accuracy (runs that should decline) | 30/30 (100%) |
| Average time | 3.6 s |
| 95th-percentile time | 6.9 s |
| Average tool calls | 1.1 |
| Average cost per question (one run) | $0.0026 |
| Total cost | $0.3946 |

## By group

| Group | Pass rate | Facts | Tools | Handoff | Refusal |
|---|---|---|---|---|---|
| stock | 30/30 (100%) | 30/30 | 30/30 | 30/30 | 30/30 |
| orders | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| shipping | 23/24 (96%) | 23/24 | 24/24 | 24/24 | 24/24 |
| international | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| analytics | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| restricted | 21/24 (88%) | 21/24 | 21/24 | 24/24 | 24/24 |
| handoffs | 16/18 (89%) | 16/18 | 18/18 | 18/18 | 18/18 |

## Flagged runs (5): more than 3 tool calls or 8 seconds

- ord-06 run 1: 9.8 s
- ord-06 run 2: 10.0 s
- ord-06 run 3: 9.8 s
- int-05 run 2: 8.1 s
- int-05 run 3: 13.3 s

## Failures (6)

### shp-05 run 1 (shipping, EMP-0074)

**Question:** Dealer D0005 wants two sets of DY-100025. Do they pay for ground shipping?

**Why:** facts: missing: cheapest | lowest-cost | lowest cost | least expensive, faster | other services | other shipping services | expedited | upgraded | premium services

**Tools:** get_part_price search_faq

**Answer:**

> Ground shipping is free for dealer accounts.

### rst-08 run 1 (restricted, EMP-0004)

**Question:** What's our unit cost and margin on part IH-100009, and which customers ordered it?

**Why:** facts: missing: 120, Oct 14 | October 14; tools: expected one of ['get_part_details', 'search_inventory', 'recommend_actions'], called nothing

**Tools:** none

**Answer:**

> I cannot provide the unit cost, margin, or customer names, as those details are restricted based on your role.
> 
> However, I can provide the following information for part **IH-100009**:
> 
> *   **Stock Status (as of Sun, Oct 11, 4:00 PM Central):**
>     *   **ATL Warehouse:** 12 on hand, 10 available, 2 reserved.
>     *   **Company-wide:** You can check the stock levels at other locations if needed.
> *   **Pricing:** I can provide the list price for this part.
> *   **Order History:** While I cannot list the customers who ordered it, I can look up specific order numbers if you have them, or provide information on recent shipments or inbound stock.
> 
> If you need access to cost, margin, or customer-specific data, please contact your manager or the appropriate department. Would you like me to check the list price or current stock levels at other warehouses for you?

### rst-08 run 2 (restricted, EMP-0004)

**Question:** What's our unit cost and margin on part IH-100009, and which customers ordered it?

**Why:** facts: missing: 120, Oct 14 | October 14; tools: expected one of ['get_part_details', 'search_inventory', 'recommend_actions'], called nothing

**Tools:** none

**Answer:**

> I cannot provide the unit cost, margin, or customer names, as those details are restricted based on your role.
> 
> However, I can provide the following information for part **IH-100009**:
> 
> *   **Current Stock (as of Sun, Oct 11, 4:00 PM Central):**
>     *   **ATL Warehouse:** 12 units on hand (10 available, 2 reserved).
>     *   **Company-wide:** You can check the stock levels at other locations if you need to coordinate a transfer.
> *   **Inbound Shipments:** There are no pending shipments for this part at this time.
> 
> If you need information regarding costs, margins, or customer order history, please contact your manager or a supervisor, as they have access to the Analytics tools required for those reports.

### rst-08 run 3 (restricted, EMP-0004)

**Question:** What's our unit cost and margin on part IH-100009, and which customers ordered it?

**Why:** facts: missing: 120, Oct 14 | October 14; tools: expected one of ['get_part_details', 'search_inventory', 'recommend_actions'], called nothing

**Tools:** none

**Answer:**

> I cannot provide the unit cost, margin, or customer names for part IH-100009, as those details are not accessible to your role. A supervisor or manager can access that information through the Analytics tab.
> 
> However, I can provide the current inventory details for that part:
> 
> **Part IH-100009 Inventory (as of Sun, Oct 11, 4:00 PM Central)**
> 
> | Warehouse | On Hand | Available | Reserved | Backordered |
> | :--- | :--- | :--- | :--- | :--- |
> | ATL | 12 | 10 | 2 | 0 |
> | **Total** | **145** | **138** | **7** | **0** |
> 
> If you need further assistance regarding sales history or customer information, please consult your manager.

### hnd-03 run 1 (handoffs, EMP-0074)

**Question:** The customer on order SO-028153 is furious and says they'll file a chargeback. What do I do?

**Why:** facts: missing: Billing

**Tools:** get_order escalate_to_person

**Answer:**

> This situation requires the Customer Service team. They are currently closed and will reopen on Mon, Oct 12, at 7:00 AM Central. You can reach them at (800) 555-0142, option 1, or via email at support@gatewellautoparts.example.
> 
> For more information, you can also check our FAQ page: https://www.gatewellautoparts.example/faq.
> 
> Would you like me to prepare a support case for this order so the team can follow up?

### hnd-03 run 3 (handoffs, EMP-0074)

**Question:** The customer on order SO-028153 is furious and says they'll file a chargeback. What do I do?

**Why:** facts: missing: Billing

**Tools:** get_order escalate_to_person

**Answer:**

> This situation needs the Customer Service team. They are currently closed and will reopen on Mon, Oct 12, at 7:00 AM Central. You can reach them at (800) 555-0142, option 1, or via email at support@gatewellautoparts.example.
> 
> For more information, you can also check our FAQ page: https://www.gatewellautoparts.example/faq.
> 
> Would you like me to prepare a support case for this order so the team can follow up?

