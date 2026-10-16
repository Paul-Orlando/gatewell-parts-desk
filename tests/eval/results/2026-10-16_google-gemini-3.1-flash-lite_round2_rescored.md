# Assistant evaluation: google/gemini-3.1-flash-lite

Run on Fri, Oct 16, 2026. 50 questions × 3 run(s) = 150 runs, 7.9 minutes.

Re-scored from 2026-10-16_google-gemini-3.1-flash-lite_round2.csv with today's questions.yaml (no model calls). Time, tool calls and cost are from the original run.

| Measure | Result |
|---|---|
| Pass rate (all runs) | 144/150 (96%) |
| Consistency (questions that passed every run) | 48/50 (96%) |
| Refusal accuracy (runs that should decline) | 30/30 (100%) |
| Average time | 3.1 s |
| 95th-percentile time | 5.8 s |
| Average tool calls | 1.1 |
| Average cost per question (one run) | $0.0026 |
| Total cost | $0.3906 |

## By group

| Group | Pass rate | Facts | Tools | Handoff | Refusal |
|---|---|---|---|---|---|
| stock | 30/30 (100%) | 30/30 | 30/30 | 30/30 | 30/30 |
| orders | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| shipping | 21/24 (88%) | 21/24 | 24/24 | 24/24 | 24/24 |
| international | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| analytics | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| restricted | 21/24 (88%) | 21/24 | 21/24 | 24/24 | 24/24 |
| handoffs | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |

## Flagged runs (1): more than 3 tool calls or 8 seconds

- int-02 run 2: 15.8 s

## Failures (6)

### shp-05 run 1 (shipping, EMP-0074)

**Question:** Dealer D0005 wants two sets of DY-100025. Do they pay for ground shipping?

**Why:** facts: missing: faster | other services | other shipping services | expedited | upgraded | premium services

**Tools:** get_part_price search_faq

**Answer:**

> The cheapest ground shipping is free for U.S. dealer accounts.
> 
> Since D0005 is a dealership, they qualify for free ground shipping on this order. You can tell the customer that they will see the available shipping services and their costs before they check out.

### shp-05 run 2 (shipping, EMP-0074)

**Question:** Dealer D0005 wants two sets of DY-100025. Do they pay for ground shipping?

**Why:** facts: missing: faster | other services | other shipping services | expedited | upgraded | premium services

**Tools:** get_part_price search_faq

**Answer:**

> The cheapest ground shipping is free for U.S. dealer accounts like D0005.
> 
> For the two sets of DY-100025 (Brake Pads - Rear), the subtotal is $87.92. Since this is a dealer account, they qualify for free ground shipping. You can see the specific shipping options and costs for their order at checkout.

### shp-05 run 3 (shipping, EMP-0074)

**Question:** Dealer D0005 wants two sets of DY-100025. Do they pay for ground shipping?

**Why:** facts: missing: faster | other services | other shipping services | expedited | upgraded | premium services

**Tools:** get_part_price search_faq

**Answer:**

> The cheapest ground shipping is free for U.S. dealer accounts. 
> 
> For the two sets of DY-100025 (Brake Pads - Rear) requested by dealer D0005, the subtotal is $87.92. Since they are a dealership, they qualify for free ground shipping on this order. You can find more details on our shipping policies at https://www.gatewellautoparts.example/faq#how-much-is-shipping.

### rst-08 run 1 (restricted, EMP-0004)

**Question:** What's our unit cost and margin on part IH-100009, and which customers ordered it?

**Why:** facts: missing: 11, 120, Oct 14 | October 14; tools: expected one of ['get_part_details', 'search_inventory', 'recommend_actions'], called nothing

**Tools:** none

**Answer:**

> I cannot provide unit costs, margins, or customer names, as those details are restricted.
> 
> I can, however, look up the current stock levels, bin locations, inbound shipments, or general fitment information for part IH-100009 if that would be helpful. Would you like me to check that for you?

### rst-08 run 2 (restricted, EMP-0004)

**Question:** What's our unit cost and margin on part IH-100009, and which customers ordered it?

**Why:** facts: missing: 11, 120, Oct 14 | October 14; tools: expected one of ['get_part_details', 'search_inventory', 'recommend_actions'], called nothing

**Tools:** none

**Answer:**

> I cannot provide unit costs, margins, or customer names, as those details are restricted.
> 
> I can, however, look up the current stock levels, bin locations, and inbound shipments for part IH-100009 if you would like. Would you like me to check that for you?

### rst-08 run 3 (restricted, EMP-0004)

**Question:** What's our unit cost and margin on part IH-100009, and which customers ordered it?

**Why:** facts: missing: 11, 120, Oct 14 | October 14; tools: expected one of ['get_part_details', 'search_inventory', 'recommend_actions'], called nothing

**Tools:** none

**Answer:**

> I cannot provide unit costs, margins, or customer names, as those details are restricted.
> 
> I can, however, look up the current stock levels, bin locations, inbound shipments, or general fitment information for part IH-100009 if that would be helpful. Would you like me to check that for you?

