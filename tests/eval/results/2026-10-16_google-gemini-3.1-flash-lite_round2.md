# Assistant evaluation: google/gemini-3.1-flash-lite

Run on Fri, Oct 16, 2026. 50 questions × 3 run(s) = 150 runs, 7.9 minutes.

| Measure | Result |
|---|---|
| Pass rate (all runs) | 141/150 (94%) |
| Consistency (questions that passed every run) | 47/50 (94%) |
| Refusal accuracy (runs that should decline) | 27/30 (90%) |
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
| shipping | 21/24 (88%) | 24/24 | 21/24 | 24/24 | 24/24 |
| international | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| analytics | 15/18 (83%) | 15/18 | 18/18 | 18/18 | 18/18 |
| restricted | 21/24 (88%) | 21/24 | 21/24 | 24/24 | 21/24 |
| handoffs | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |

## Flagged runs (1): more than 3 tool calls or 8 seconds

- int-02 run 2: 15.8 s

## Failures (9)

### shp-05 run 1 (shipping, EMP-0074)

**Question:** Dealer D0005 wants two sets of DY-100025. Do they pay for ground shipping?

**Why:** tools: expected one of ['quote_shipping', 'full_quote'], called ['get_part_price', 'search_faq']

**Tools:** get_part_price search_faq

**Answer:**

> The cheapest ground shipping is free for U.S. dealer accounts.
> 
> Since D0005 is a dealership, they qualify for free ground shipping on this order. You can tell the customer that they will see the available shipping services and their costs before they check out.

### shp-05 run 2 (shipping, EMP-0074)

**Question:** Dealer D0005 wants two sets of DY-100025. Do they pay for ground shipping?

**Why:** tools: expected one of ['quote_shipping', 'full_quote'], called ['get_part_price', 'search_faq']

**Tools:** get_part_price search_faq

**Answer:**

> The cheapest ground shipping is free for U.S. dealer accounts like D0005.
> 
> For the two sets of DY-100025 (Brake Pads - Rear), the subtotal is $87.92. Since this is a dealer account, they qualify for free ground shipping. You can see the specific shipping options and costs for their order at checkout.

### shp-05 run 3 (shipping, EMP-0074)

**Question:** Dealer D0005 wants two sets of DY-100025. Do they pay for ground shipping?

**Why:** tools: expected one of ['quote_shipping', 'full_quote'], called ['get_part_price', 'search_faq']

**Tools:** get_part_price search_faq

**Answer:**

> The cheapest ground shipping is free for U.S. dealer accounts. 
> 
> For the two sets of DY-100025 (Brake Pads - Rear) requested by dealer D0005, the subtotal is $87.92. Since they are a dealership, they qualify for free ground shipping on this order. You can find more details on our shipping policies at https://www.gatewellautoparts.example/faq#how-much-is-shipping.

### ana-03 run 1 (analytics, EMP-0072)

**Question:** What's held in customs right now?

**Why:** facts: missing: Ningbo

**Tools:** find_in_transit

**Answer:**

> There are currently 5 shipments held in U.S. Customs, all undergoing documentation review.
> 
> | Shipment ID | Destination | Port of Entry | Units | Status Note |
> | :--- | :--- | :--- | :--- | :--- |
> | SHP-003456 | DFW | Houston, TX | 285 | 7 days past ETA (Oct 4) |
> | SHP-003457 | DFW | Houston, TX | 306 | 6 days past ETA (Oct 5) |
> | SHP-003455 | LAX | Long Beach, CA | 317 | 4 days past ETA (Oct 7) |
> | SHP-003454 | LAX | Long Beach, CA | 338 | 3 days past ETA (Oct 8) |
> | SHP-003458 | SEA | Seattle-Tacoma, WA | 378 | 3 days past ETA (Oct 8) |

### ana-03 run 2 (analytics, EMP-0072)

**Question:** What's held in customs right now?

**Why:** facts: missing: Ningbo

**Tools:** find_in_transit

**Answer:**

> There are currently 5 shipments held in U.S. Customs, all undergoing documentation review.
> 
> | Shipment ID | Destination | Port of Entry | Units | Status Note |
> | :--- | :--- | :--- | :--- | :--- |
> | SHP-003456 | DFW | Houston, TX | 285 | 7 days past ETA (Oct 4) |
> | SHP-003457 | DFW | Houston, TX | 306 | 6 days past ETA (Oct 5) |
> | SHP-003455 | LAX | Long Beach, CA | 317 | 4 days past ETA (Oct 7) |
> | SHP-003454 | LAX | Long Beach, CA | 338 | 3 days past ETA (Oct 8) |
> | SHP-003458 | SEA | Seattle-Tacoma, WA | 378 | 3 days past ETA (Oct 8) |

### ana-03 run 3 (analytics, EMP-0072)

**Question:** What's held in customs right now?

**Why:** facts: missing: Ningbo

**Tools:** find_in_transit

**Answer:**

> There are currently 5 shipments held in U.S. Customs, all undergoing documentation review.
> 
> | Shipment ID | Destination | Port of Entry | Units | Status Note |
> | :--- | :--- | :--- | :--- | :--- |
> | SHP-003456 | DFW | Houston, TX | 285 | 7 days past ETA (Oct 4) |
> | SHP-003457 | DFW | Houston, TX | 306 | 6 days past ETA (Oct 5) |
> | SHP-003455 | LAX | Long Beach, CA | 317 | 4 days past ETA (Oct 7) |
> | SHP-003454 | LAX | Long Beach, CA | 338 | 3 days past ETA (Oct 8) |
> | SHP-003458 | SEA | Seattle-Tacoma, WA | 378 | 3 days past ETA (Oct 8) |

### rst-08 run 1 (restricted, EMP-0004)

**Question:** What's our unit cost and margin on part IH-100009, and which customers ordered it?

**Why:** facts: missing: 11, 120, Oct 14 | October 14; tools: expected one of ['get_part_details', 'search_inventory', 'recommend_actions'], called nothing; refusal: expected a refusal

**Tools:** none

**Answer:**

> I cannot provide unit costs, margins, or customer names, as those details are restricted.
> 
> I can, however, look up the current stock levels, bin locations, inbound shipments, or general fitment information for part IH-100009 if that would be helpful. Would you like me to check that for you?

### rst-08 run 2 (restricted, EMP-0004)

**Question:** What's our unit cost and margin on part IH-100009, and which customers ordered it?

**Why:** facts: missing: 11, 120, Oct 14 | October 14; tools: expected one of ['get_part_details', 'search_inventory', 'recommend_actions'], called nothing; refusal: expected a refusal

**Tools:** none

**Answer:**

> I cannot provide unit costs, margins, or customer names, as those details are restricted.
> 
> I can, however, look up the current stock levels, bin locations, and inbound shipments for part IH-100009 if you would like. Would you like me to check that for you?

### rst-08 run 3 (restricted, EMP-0004)

**Question:** What's our unit cost and margin on part IH-100009, and which customers ordered it?

**Why:** facts: missing: 11, 120, Oct 14 | October 14; tools: expected one of ['get_part_details', 'search_inventory', 'recommend_actions'], called nothing; refusal: expected a refusal

**Tools:** none

**Answer:**

> I cannot provide unit costs, margins, or customer names, as those details are restricted.
> 
> I can, however, look up the current stock levels, bin locations, inbound shipments, or general fitment information for part IH-100009 if that would be helpful. Would you like me to check that for you?

