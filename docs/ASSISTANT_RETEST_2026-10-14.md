# Retest after fixes: 2026-10-14 (evening)

> Names updated to fictional equivalents on 2026-10-16; numbers unchanged.

- **Model:** Gemini 3.1 Flash-Lite via OpenRouter. Demo mode off.
- **Covers:** the fixes from `docs/ASSISTANT_TEST_2026-10-14.md`, plus the new analytics category filter and the click-through to parts.
- **Method:** every number was checked against the app's own API.

## Assistant: 9 of 9 pass

| # | Role | Question | Result | Time | Tool calls |
|---|---|---|---|---|---|
| 1 | Operations Director | Most missing stock, categories, value at cost | PASS: Newark, 140 units, $4,951 (all exact) | 3.5 s | 1 (was 8 and failed) |
| 2 | Operations Director | What's held in customs right now? | PASS: 5 Ningbo shipments, 1,624 units, correct ports | 2.4 s | 1 |
| 3 | CS Rep | Bumper cover, carrier comparison to Dallas | PASS: now lists OEM and Premium options and asks which one; Postara ruled out | 4.2 s | 2 |
| 4 | CS Rep | $400 refund, upset customer | PASS: hands off to Returns & Cores; says "You can tell the customer…"; offers to open a support case | 2.7 s | 1 |
| 5 | Warehouse Associate | Unit cost, margin and customers for IH-100009 | PASS: refuses, then offers what the associate can see (0 available at ATL, 11 backordered, 120 inbound, ETA Oct 14) | 2.6 s | 1 |
| 6 | CS Rep | 2 front struts for a 2018 Torvik to Toronto, total in CAD | PASS: both options in CAD with 5% GST; C$837.40 (OEM) and C$645.01 (Value) by Velocair Ground match the quote engine exactly | 4.1 s | 3 |
| 7 | CS Rep | Weather in Atlanta (off-topic) | PASS: polite decline | 1.1 s | 0 |
| — | Server | Unknown warehouse code (CHI) | PASS: HTTP 400 listing the 11 valid codes | — | — |
| — | Server | Atlanta manager requests LAX with a category | PASS: still limited to ATL | — | — |

## Analytics: pass

- **Category filter:** narrows every panel. Newark plus Sensors shows 88 missing units, $2,997, which matches the data. It works at phone width.
- **Explanation note:** "Shipping and exchange figures cover whole orders, so they aren't split by category." Good.
- **Click-through:** part numbers in "Low stock to reorder" open the part detail drawer (tested with FM-100192).
- **Sales chart:** "Units sold per month" in the drawer renders as a 12-month bar chart with a table view.
- **Console:** no errors from the app.

## Remaining small issues, in priority order

1. **Internal tool name leaked:** the reply to the warehouse associate said "via the `contact_team` tool". Add a system-prompt rule: never mention tool names or internal terms; offer the action in plain words (for example, "I can give you the Billing team's contact details").
2. **Tax claim beyond the data:** the Toronto answer said provincial taxes "will be collected at checkout". The data only says "GST 5% collected at checkout (DDP); provincial tax extra". Add a prompt rule: state tax and policy text exactly as the tools return it; don't add details.
3. **Wrong breakdown level:** for "Which warehouse has the most missing stock, which categories…", the category breakdown was company-wide rather than Newark's. It was labeled honestly. Newark's own top categories are Sensors (88 units, $2,997) and Ignition (49, $1,757). Add a prompt hint: when a follow-up part of a question is about the warehouse just identified, call the section again with that `warehouse`.
4. **Customs ETAs left out:** the customs answer didn't say the shipments are past their ETAs. Optional: include the ETA and a "days late" figure in the `find_in_transit` results.
5. **Analytics "Your view" line:** still reads "All warehouses" when Warehouse = NWK and Category = Sensors are selected. Show the active filters, for example "Showing: Newark, Sensors".
6. **Single-bar chart:** with a category selected, "Revenue by category" shows one bar. In that case, hide it or replace it with "Top parts in this category".
