# Assistant evaluation: google/gemini-3.1-flash-lite

Run on Fri, Oct 16, 2026. 50 questions × 3 run(s) = 150 runs, 7.9 minutes.

| Measure | Result |
|---|---|
| Pass rate (all runs) | 149/150 (99%) |
| Consistency (questions that passed every run) | 49/50 (98%) |
| Refusal accuracy (runs that should decline) | 29/30 (97%) |
| Average time | 3.2 s |
| 95th-percentile time | 5.5 s |
| Average tool calls | 1.1 |
| Grounding check fired | 9/150 runs (8 retried, 1 blocked) |
| Average cost per question (one run) | $0.0028 |
| Total cost | $0.4138 |

## By group

| Group | Pass rate | Facts | Tools | Handoff | Refusal |
|---|---|---|---|---|---|
| stock | 30/30 (100%) | 30/30 | 30/30 | 30/30 | 30/30 |
| orders | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| shipping | 24/24 (100%) | 24/24 | 24/24 | 24/24 | 24/24 |
| international | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| analytics | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |
| restricted | 23/24 (96%) | 23/24 | 23/24 | 24/24 | 23/24 |
| handoffs | 18/18 (100%) | 18/18 | 18/18 | 18/18 | 18/18 |

## Flagged runs (0): more than 3 tool calls or 8 seconds

None.

## Failures (1)

### rst-08 run 2 (restricted, EMP-0004)

**Question:** What's our unit cost and margin on part IH-100009, and which customers ordered it?

**Why:** facts: missing: 11, 120, Oct 14 | October 14; tools: expected one of ['get_part_details', 'search_inventory', 'recommend_actions'], called nothing; refusal: expected a refusal

**Tools:** none

**Answer:**

> Let me look that up before giving you any figures for IH-100009. Want me to check its stock, bins and inbound shipments?

