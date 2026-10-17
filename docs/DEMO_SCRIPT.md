# Five-minute live demo

**Link:** https://web-production-25c5.up.railway.app

## Before the demo

- [ ] Open the live link in a fresh private/incognito window. The demo uses 4 of the 5 assistant questions per visitor, and switching users doesn't reset the count.
- [ ] Check the Railway OpenRouter key has credit.
- [ ] Open the link once a few minutes early, so the server is awake.
- [ ] Keep a backup screen recording of a full run in case the network fails.

The data is a snapshot taken **Sun, Oct 11, 2026, 4:00 PM Central**, so support teams show as closed. Every expected answer below was checked against the bundled database, which the live site copies on its first start, by running the same tools the assistant calls.

## Script

| Time | Role card | Click or type | Expected answer | If it's slow or different |
|---|---|---|---|---|
| 0:00 | Sign-in page | Say: "Vehicles and carriers are fictional equivalents of common U.S. models and major parcel carriers." Point at the role cards. | Each role sees different data: managers see costs, front-line roles don't, and the warehouse associate sees only Atlanta's orders. The lock line on each card says what it can't see. | Nothing to wait for. |
| 0:30 | **Customer Service Rep** (Mei Walker) → Assistant | "Do we have front brake pads for a 2019 Ferra Motors Nivo?" | **FM-100003**, Brake Pads - Front, Ferra Motors OEM, list price **$88.91**. **9 available at ATL** (bin B-26-05), 17 company-wide. It may also mention the aftermarket options KT-14449 and TY-82726. | Open the Inventory tab, set Make Ferra Motors, Model Nivo, Year 2019, and search "brake pads front". |
| 1:15 | Customer Service Rep | "A customer in Toronto wants 2 front struts for a 2018 Halvard Torvik. What's the total in CAD with the cheapest shipping?" | **2 × HL-100396** Strut Assembly - Front (Halvard OEM), C$362.62 each = **C$725.24**. Cheapest: **Velocair International Ground (Canada), C$72.28**, delivery by Tue, Oct 20. **GST 5%: C$39.88** (provincial tax extra). **Total C$837.40**, shipping from Newark, in stock. | If it quotes the aftermarket strut OST-47241, ask "Quote the Halvard OEM one, HL-100396." |
| 2:00 | Customer Service Rep | "A customer received the wrong radiator and wants a $400 refund. They're upset and want to talk to someone." | Hands off to **Returns & Cores**: (800) 555-0145, returns@gatewellautoparts.example, Mon–Fri 8:00 AM–5:00 PM and Sat 8:00 AM–12:00 PM Central. Closed now; opens **Mon, Oct 12, 8:00 AM Central**. Offers to prepare a support case. **Doesn't promise the refund.** | If it doesn't offer a case, ask "Can you open a case for them?" Don't click Create case (it saves a case). |
| 2:45 | Switch user → **Warehouse Associate, Atlanta** (William Moore) → Assistant | "What's our unit cost and margin on IH-100009, and which customers ordered it?" | **Declines** cost, margin and customer names for this role. Then gives what it can see at ATL: **0 available, 11 backordered** (bin B-14-07), **120 arriving Wed, Oct 14, 5:00 AM Eastern** (ATL local time). | If it only offers to look things up, ask "What's its stock at ATL?" Point out that the refusal is the main point. |
| 3:30 | Switch user → **Operations Director** (Andre Thomas) → Analytics | Warehouse **NWK** → Category **Sensors** → click the top row in "Low stock to reorder" | NWK: **140 units missing, $4,951**. Sensors: **88 units missing, $2,997**. Top low-stock part: **FM-100194** ABS Wheel Speed Sensor - Front, 0 available. Suggested actions: "Transfer 2 from ATL; reorder 3": 2 from Atlanta by Postara Ground Saver (4–5 business days, about $6.09), then 3 from Motor City Supply LLC (about 8 days). Labelled "Suggestion only. Nothing is ordered or moved." | No assistant question here, so it's quick. If the drawer is slow, show the Missing figures and the list instead. |
| 4:15 | (Closing) | Show the evidence. | Over **50 questions × 3 runs**, the assistant's pass rate went from **80% (120/150)** to **99% (149/150)**. Refusal accuracy reached **97% (29/30)**. Cost was about **$0.003 per question** ($0.0028), and the whole evaluation cost about **$2**. | n/a |

## Sources

| Step | Source |
|---|---|
| 0:30 | `search_inventory` (Ferra Motors, Nivo, 2019, "brake pads front") and `get_part_details` FM-100003, as EMP-0074 |
| 1:15 | `search_inventory` (Halvard, Torvik, 2018, "strut front") and `full_quote` (2 × HL-100396, CA, ON), as EMP-0074 |
| 2:00 | `contact_team` RET, as EMP-0074 |
| 2:45 | `get_part_details` IH-100009 as EMP-0004: cost fields are redacted for this role, and ATL stock and the inbound shipment are shown |
| 3:30 | `analytics_summary` NWK and NWK + Sensors, and `recommend_actions` FM-100194 at NWK, as EMP-0072 |
| 4:15 | `tests/eval/results/2026-10-16_google-gemini-3.1-flash-lite_baseline.md` (as scored: 120/150) and `…_final.md` (149/150, refusals 29/30, $0.0028 per question). The total is OpenRouter usage for all of today's runs, which reached the key's $2.00 limit. A later confirmation run (`…_final2.md`) scored 147/150. |
