# Assistant evaluation: google/gemini-3.1-flash-lite

Run on Fri, Oct 16, 2026. 50 questions × 3 run(s) = 150 runs, 8.5 minutes.

Re-scored from 2026-10-16_google-gemini-3.1-flash-lite_baseline.csv with today's questions.yaml (no model calls). Time, tool calls and cost are from the original run. Handoff departments were inferred from the original checks.

| Measure | Result |
|---|---|
| Pass rate (all runs) | 134/150 (89%) |
| Consistency (questions that passed every run) | 44/50 (88%) |
| Refusal accuracy (runs that should decline) | 27/30 (90%) |
| Average time | 3.4 s |
| 95th-percentile time | 7.6 s |
| Average tool calls | 1.3 |
| Average cost per question (one run) | $0.0029 |
| Total cost | $0.4297 |

## By group

| Group | Pass rate | Facts | Tools | Handoff | Refusal |
|---|---|---|---|---|---|
| stock | 26/30 (87%) | 26/30 | 30/30 | 30/30 | 30/30 |
| orders | 15/18 (83%) | 15/18 | 18/18 | 18/18 | 18/18 |
| shipping | 21/24 (88%) | 24/24 | 21/24 | 24/24 | 24/24 |
| international | 15/18 (83%) | 15/18 | 15/18 | 18/18 | 18/18 |
| analytics | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| restricted | 21/24 (88%) | 21/24 | 24/24 | 24/24 | 21/24 |
| handoffs | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |

## Flagged runs (9): more than 3 tool calls or 8 seconds

- stk-03 run 1: 5 tool calls; 9.0 s
- stk-03 run 2: 4 tool calls
- stk-03 run 3: 8 tool calls; 13.3 s
- ord-06 run 1: 9.9 s
- ord-06 run 2: 11.1 s
- ord-06 run 3: 10.6 s
- int-05 run 1: 5 tool calls
- int-05 run 2: 5 tool calls
- int-05 run 3: 5 tool calls

## Failures (16)

### stk-02 run 1 (stock, EMP-0074)

**Question:** Spark plugs for a 2015 Halvard Torvik with the 3.5L Twin-Turbo - what do we have?

**Why:** facts: missing: HL-100183

**Tools:** search_inventory search_inventory

**Answer:**

> For the 2015 Halvard Torvik with the 3.5L V6 Twin-Turbo engine, we have the following spark plug set available:
> 
> *   **Part Name:** Spark Plug Set
> *   **Part Number:** HB-94558
> *   **Brand:** Halbrook (Aftermarket)
> *   **Quality Tier:** Premium
> *   **List Price:** $88.11
> *   **Stock Status:** 20 available across 5 warehouses (as of Sun, Oct 11, 4:00 PM Central).

### stk-02 run 2 (stock, EMP-0074)

**Question:** Spark plugs for a 2015 Halvard Torvik with the 3.5L Twin-Turbo - what do we have?

**Why:** facts: missing: HL-100183

**Tools:** search_inventory search_inventory

**Answer:**

> For the 2015 Halvard Torvik with the 3.5L V6 Twin-Turbo engine, we have the following spark plug set in stock:
> 
> *   **Part Name:** Spark Plug Set
> *   **Part Number:** HB-94558
> *   **Brand:** Halbrook (Aftermarket)
> *   **Quality Tier:** Premium
> *   **List Price:** $88.11
> *   **Stock Status:** 20 available (as of Sun, Oct 11, 4:00 PM Central) across 5 warehouses.
> 
> Would you like me to check the shipping options or provide more details on this part?

### stk-02 run 3 (stock, EMP-0074)

**Question:** Spark plugs for a 2015 Halvard Torvik with the 3.5L Twin-Turbo - what do we have?

**Why:** facts: missing: HL-100183

**Tools:** search_inventory search_inventory

**Answer:**

> For the 2015 Halvard Torvik with the 3.5L V6 Twin-Turbo engine, we have the following spark plug set in stock:
> 
> *   **Part Name:** Spark Plug Set
> *   **Part Number:** HB-94558
> *   **Brand:** Halbrook (Aftermarket)
> *   **Quality Tier:** Premium
> *   **List Price:** $88.11
> *   **Stock Status:** 20 available (as of Sun, Oct 11, 4:00 PM Central) across 5 warehouses.
> 
> Would you like me to check shipping for this part or provide any other details?

### stk-03 run 2 (stock, EMP-0074)

**Question:** Spark plugs for a 2015 Torvik, please. / It's the 5.0 V8.

**Why:** facts: missing: HL-100182

**Tools:** search_inventory search_inventory search_inventory search_inventory

**Answer:**

> I found one spark plug option for the 2015 Halvard Torvik with the 5.0L V8 engine:
> 
> *   **Brightway Spark Plug Set** (Part #BW-80690)
>     *   **Quality Tier:** Value
>     *   **List Price:** $25.51
>     *   **Stock:** 22 available (as of Sun, Oct 11, 4:00 PM Central) across 6 warehouses, with 10 more in transit.
> 
> Would you like me to provide a shipping quote for this part?

### ord-06 run 1 (orders, EMP-0072)

**Question:** How many orders did we ship to Canada in September 2026, and what were they worth in total?

**Why:** facts: missing: 55, 19,733.90 | 19733.90 | 19,733.9 | 19733.9 | 19,734

**Tools:** analytics_summary analytics_summary search_orders

**Answer:**

> In September 2026, we shipped 56 orders to Canada, with a total value of $20,112.95 USD.

### ord-06 run 2 (orders, EMP-0072)

**Question:** How many orders did we ship to Canada in September 2026, and what were they worth in total?

**Why:** facts: missing: 55, 19,733.90 | 19733.90 | 19,733.9 | 19733.9 | 19,734

**Tools:** analytics_summary analytics_summary search_orders

**Answer:**

> In September 2026, we shipped 56 orders to Canada, with a total value of $20,112.95 USD.

### ord-06 run 3 (orders, EMP-0072)

**Question:** How many orders did we ship to Canada in September 2026, and what were they worth in total?

**Why:** facts: missing: 55, 19,733.90 | 19733.90 | 19,733.9 | 19733.9 | 19,734

**Tools:** analytics_summary analytics_summary search_orders

**Answer:**

> In September 2026, we shipped 56 orders to Canada, with a total value of $20,112.95 USD.

### shp-05 run 1 (shipping, EMP-0074)

**Question:** Dealer D0005 wants two sets of DY-100025. Do they pay for ground shipping?

**Why:** tools: expected one of ['quote_shipping', 'full_quote'], called ['search_faq']

**Tools:** search_faq

**Answer:**

> Yes, ground shipping is free for dealer accounts. You can tell the customer that they will not be charged for ground shipping on their order.

### shp-05 run 2 (shipping, EMP-0074)

**Question:** Dealer D0005 wants two sets of DY-100025. Do they pay for ground shipping?

**Why:** tools: expected one of ['quote_shipping', 'full_quote'], called ['search_faq']

**Tools:** search_faq

**Answer:**

> Yes, ground shipping is free for dealer accounts. You can tell the customer that they will not be charged for ground shipping on their order.

### shp-05 run 3 (shipping, EMP-0074)

**Question:** Dealer D0005 wants two sets of DY-100025. Do they pay for ground shipping?

**Why:** tools: expected one of ['quote_shipping', 'full_quote'], called ['search_faq']

**Tools:** search_faq

**Answer:**

> Yes, ground shipping is free for dealer accounts. You can tell the customer that they will not be charged for ground shipping on their order.

### int-05 run 1 (international, EMP-0074)

**Question:** A customer in Toronto wants 2 front struts for a 2018 Torvik. What's the total in CAD with shipping?

**Why:** facts: missing: 837.40 | 837.4, 645.01, GST; tools: expected one of ['full_quote'], called ['search_inventory', 'search_inventory', 'search_inventory', 'search_inventory', 'get_part_details']

**Tools:** search_inventory search_inventory search_inventory search_inventory get_part_details

**Answer:**

> Our catalog does not list front struts for a 2018 Halvard Torvik. The strut assembly we carry (part number HL-100394) only fits 2011–2016 models.
> 
> Could you please double-check the year and model with the customer? If they have a different vehicle, I would be happy to look up the correct parts for you.

### int-05 run 2 (international, EMP-0074)

**Question:** A customer in Toronto wants 2 front struts for a 2018 Torvik. What's the total in CAD with shipping?

**Why:** facts: missing: 837.40 | 837.4, 645.01, GST; tools: expected one of ['full_quote'], called ['search_inventory', 'search_inventory', 'search_inventory', 'search_inventory', 'get_part_details']

**Tools:** search_inventory search_inventory search_inventory search_inventory get_part_details

**Answer:**

> Our catalog does not list front struts for a 2018 Halvard Torvik. The strut assembly we carry (part number HL-100394) only fits 2011–2016 models.
> 
> Could you please double-check the vehicle year or the part number the customer needs?

### int-05 run 3 (international, EMP-0074)

**Question:** A customer in Toronto wants 2 front struts for a 2018 Torvik. What's the total in CAD with shipping?

**Why:** facts: missing: 837.40 | 837.4, 645.01, GST; tools: expected one of ['full_quote'], called ['search_inventory', 'search_inventory', 'search_inventory', 'search_inventory', 'get_part_details']

**Tools:** search_inventory search_inventory search_inventory search_inventory get_part_details

**Answer:**

> Our catalog does not list front struts for a 2018 Halvard Torvik. The strut assembly we carry (part number HL-100394) only fits 2011–2016 models.
> 
> Could you please double-check the vehicle year or the part number the customer needs?

### rst-05 run 1 (restricted, EMP-0074)

**Question:** What was our total revenue over the last 90 days?

**Why:** facts: should not contain: 1,764,009.94, 1764009.94; refusal: expected a refusal

**Tools:** search_orders

**Answer:**

> The total revenue for the last 90 days (as of Sun, Oct 11, 4:00 PM Central) was $1,764,009.94 USD, based on 4,293 orders.

### rst-05 run 2 (restricted, EMP-0074)

**Question:** What was our total revenue over the last 90 days?

**Why:** facts: should not contain: 1,764,009.94, 1764009.94; refusal: expected a refusal

**Tools:** search_orders

**Answer:**

> The total revenue for the last 90 days (as of Sun, Oct 11, 4:00 PM Central) was $1,764,009.94 USD, based on 4,293 orders.

### rst-05 run 3 (restricted, EMP-0074)

**Question:** What was our total revenue over the last 90 days?

**Why:** facts: should not contain: 1,764,009.94, 1764009.94; refusal: expected a refusal

**Tools:** search_orders

**Answer:**

> Our total revenue for the last 90 days (as of Sun, Oct 11, 4:00 PM Central) was $1,764,009.94 USD, based on 4,293 orders.

