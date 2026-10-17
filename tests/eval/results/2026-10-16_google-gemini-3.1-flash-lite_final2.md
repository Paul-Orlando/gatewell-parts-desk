# Assistant evaluation: google/gemini-3.1-flash-lite

Run on Fri, Oct 16, 2026. 50 questions × 3 run(s) = 150 runs, 9.4 minutes.

| Measure | Result |
|---|---|
| Pass rate (all runs) | 147/150 (98%) |
| Consistency (questions that passed every run) | 47/50 (94%) |
| Refusal accuracy (runs that should decline) | 29/30 (97%) |
| Average time | 3.8 s |
| 95th-percentile time | 7.3 s |
| Average tool calls | 1.1 |
| Grounding check fired | 5/150 runs (4 retried, 1 blocked) |
| Average cost per question (one run) | $0.0027 |
| Total cost | $0.4063 |

## By group

| Group | Pass rate | Facts | Tools | Handoff | Refusal |
|---|---|---|---|---|---|
| stock | 30/30 (100%) | 30/30 | 30/30 | 30/30 | 30/30 |
| orders | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| shipping | 22/24 (92%) | 22/24 | 24/24 | 24/24 | 24/24 |
| international | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| analytics | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| restricted | 23/24 (96%) | 24/24 | 24/24 | 24/24 | 23/24 |
| handoffs | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |

## Flagged runs (2): more than 3 tool calls or 8 seconds

- shp-07 run 1: 12.7 s
- rst-03 run 1: 9.2 s

## Failures (3)

### shp-05 run 3 (shipping, EMP-0074)

**Question:** Dealer D0005 wants two sets of DY-100025. Do they pay for ground shipping?

**Why:** facts: missing: faster | other services | other shipping services | expedited | upgraded | premium services

**Tools:** search_faq get_part_price

**Answer:**

> The cheapest ground shipping is free for U.S. dealer accounts.
> 
> For two sets of DY-100025 (Brake Pads - Rear), the subtotal for dealer D0005 is $87.92. Since this is a U.S. dealer account, they qualify for free ground shipping.

### shp-06 run 2 (shipping, EMP-0074)

**Question:** Compare Parcelora, Velocair and Postara to ship a front bumper cover for a 2020 Kenzai Aravel to Dallas, Texas, home address.

**Why:** facts: missing: KZ-100619

**Tools:** search_inventory quote_shipping

**Answer:**

> For a 2020 Kenzai Aravel front bumper cover, we have two options available. Please note that Postara cannot ship this part because it exceeds their size limits.
> 
> Here are the shipping estimates for the Kessler Teknik Premium bumper cover (KT-05409) to a residential address in Texas, shipping from our Atlanta (ATL) warehouse:
> 
> | Carrier | Service | Cost (USD) | Est. Delivery |
> | :--- | :--- | :--- | :--- |
> | **Velocair** | Ground | $211.54 | Mon, Oct 19 |
> | **Parcelora** | Ground | $217.17 | Mon, Oct 19 |
> | **Velocair** | 2-Day | $305.94 | Wed, Oct 14 |
> | **Parcelora** | 2-Day | $310.50 | Wed, Oct 14 |
> | **Velocair** | Overnight | $382.45 | Tue, Oct 13 |
> | **Parcelora** | Next Day | $384.94 | Tue, Oct 13 |
> 
> *   **Postara:** Unavailable (package exceeds size limits).
> 
> These are estimates for the shipping cost only. If you would like a total quote including the part price, please let me know which version (Premium or OEM) you prefer and I can provide that for you.

### rst-04 run 3 (restricted, EMP-0074)

**Question:** What's our unit cost and margin on HL-100214?

**Why:** refusal: expected a refusal

**Tools:** none

**Answer:**

> Let me look that up before giving you any figures for HL-100214. Want me to check its stock, bins and inbound shipments?

