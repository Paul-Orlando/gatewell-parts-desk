# User test script: Gatewell Parts Desk

**Goal:** see whether the assistant helps employees answer everyday questions faster and more accurately than the screens alone.
**Length:** 20 minutes per person. **People:** 3 to 5. **You need:** this script, a stopwatch, `results_template.csv`.

| Part | Time |
|---|---|
| Intro and consent | 2 min |
| Five tasks, each done two ways | 15 min |
| Three closing questions | 3 min |

---

## Before each session (facilitator)

1. Start the app with `run.bat` and open http://localhost:8000 in a **new private window** for each person. Each window starts signed out, with an empty chat.
2. The demo allows 5 assistant questions per visitor. Five tasks use five questions, and any follow-up uses another. For test sessions, either add `GATEWELL_DEMO_MODE=0` to `.env` before starting the app, or open a fresh private window if the limit is reached.
3. Check the participant's **order** in the table below and set up `results_template.csv`.
4. Have the answer key (end of this document) open where the participant can't see it.

### Order: half start with the screens, half with the assistant

Doing a task the second time is easier, whichever method comes second. So half the participants do every task **screens first**, and half do every task **assistant first**.

| Participant | Order |
|---|---|
| P1 | Screens first |
| P2 | Assistant first |
| P3 | Screens first |
| P4 | Assistant first |
| P5 | Screens first |

With 4 people, use P1 to P4 (two of each). With 3, use P1 to P3 and say so in the summary.

---

## Intro (read aloud)

> Thanks for helping. We're testing the app, not you. If something is hard, that's useful for us to know.
>
> This is a demo of an internal parts desk for an auto parts company. **Vehicles and carriers are fictional equivalents of common U.S. models and major parcel carriers.** The data is made up.
>
> I'll give you five short tasks. You'll do each one twice: once using only the screens, and once by asking the assistant. Please think out loud as you go. I'll stop each try after 3 minutes.

**Consent (read aloud, note the answer):**

> Is it OK if I time you and take notes on what you say? Your name won't be in the results.

---

## Tasks

For each task:
- Read the task card aloud and show it on paper.
- Say which method comes first for this person, and start the stopwatch when you finish reading.
- Stop the watch when they say their answer. Stop at 3 minutes (180 s) if they haven't answered, and record it as not successful.
- Write the seconds, success (yes or no) and notes in `results_template.csv`.
- Then do the same task with the other method.

**Screens only:** use any tab except Assistant (Inventory, Orders, Support cases, Support teams, Analytics).
**Assistant:** type the question in the Assistant tab. They may look at the screens to check, but the answer should come from the assistant.

Sign in with the role card named in each task. Use "Switch user" (top right) to change roles between tasks.

### Task 1: brake pads near Atlanta
**Role card:** Customer Service Rep (Mei Walker)

> A customer needs front brake pads for a **2019 Ferra Motors Nivo**. Do we have any in stock in Atlanta? Which part, and how many?

### Task 2: shipping a bumper cover to Dallas
**Role card:** Customer Service Rep (Mei Walker)

> A customer in **Dallas** wants a front bumper cover for a **2020 Daeyon Aurelle**, shipped to their home. What's the cheapest way to ship it, and when would it arrive?

### Task 3: where a part is shelved
**Role card:** Warehouse Associate, Atlanta (William Moore)

> Find part **IH-100009** in your warehouse. Which bin is it in, and when is more arriving?

### Task 4: where we are losing stock
**Role card:** Operations Director (Andre Thomas)

> Which warehouse is losing the most stock, in which category, and which part should we look at first?

### Task 5: a refund request
**Role card:** Customer Service Rep (Mei Walker)

> A customer got the wrong radiator and wants a **$400 refund**. What do you do?

---

## Closing questions (read aloud, write the answers word for word)

1. What was confusing?
2. What would you use every day?
3. On a scale of 1 to 5, how useful would the assistant be in your job? (1 = not useful, 5 = very useful)

Thank them, and close the private window.

---

## Answer key (facilitator only)

Data as of Sun, Oct 11, 2026, 4:00 PM Central. Every answer below was checked on 2026-10-16 against the database or the app's own tools, run as the role in the task. Each answer lists its source.

### Task 1: front brake pads, 2019 Ferra Motors Nivo, near Atlanta
**Answer:** yes. **FM-100003** (Ferra Motors OEM front pads, $88.91 list): **9 available at ATL**, bin B-26-05. The aftermarket options for this car (KT-14449, TY-82726) aren't stocked at ATL.

**Success:** names FM-100003 and says it's in stock at Atlanta (9). A count from another warehouse, or "no stock", is not a success.

**Source:**
- `search_inventory` as EMP-0074 with `{q: "front brake pads", year: 2019, make: "Ferra Motors", model: "Nivo", warehouse: "ATL"}` returns 1 part, FM-100003, 9 available.
- `get_part_details FM-100003` gives the bin, B-26-05 at ATL, and stock elsewhere: DFW 4, ANC 2, SEA 2.

### Task 2: front bumper cover, 2020 Daeyon Aurelle, to a home in Dallas
**Answer:** one part fits, **DY-100531** (OEM, $263.53 list). Dallas's own warehouse has none, so it **ships from Atlanta**.
- **Cheapest: Postara Ground Saver, $64.28, arrives Mon, Oct 19.** Parcelora Ground ($100.54) and Velocair Ground ($100.55) arrive the same day.
- Faster options: Parcelora 2-Day $184.47 (Wed, Oct 14) and Parcelora Next Day $253.93 (Tue, Oct 13).
- No free shipping: oversize parts aren't eligible on individual orders.

**Success:** Postara Ground Saver, about $64, arriving Mon, Oct 19. Naming a faster or dearer option as "cheapest" is not a success.

**Source:**
- `search_inventory` as EMP-0074 with `{q: "front bumper cover", year: 2020, make: "Daeyon", model: "Aurelle"}` returns 1 part, DY-100531.
- `quote_shipping` as EMP-0074 with `{items: [{part_number: "DY-100531"}], ship_to_state: "TX", residential: true}`: ships from ATL, options as above. The part drawer's Shipping quote form (Texas, Home address) uses the same quote engine.

### Task 3: IH-100009 at Atlanta
**Answer:** bin **B-14-07** at ATL. It's out of stock there: 0 available, 11 backordered. **120 arrive Wed, Oct 14 (5:00 AM local), by air** on shipment SHP-003459 from Motor City Supply LLC.

**Success:** gives bin B-14-07 and says 120 arrive Oct 14.

**Source:**
- `get_part_details IH-100009` as EMP-0004: ATL row with bin B-14-07, 0 available, 11 backordered, 120 in transit; in transit SHP-003459, Air, ETA 2026-10-14 05:00 local.
- SQL: `SELECT s.bin_location, s.qty_available, s.qty_backordered FROM v_stock_position s WHERE s.part_number = 'IH-100009' AND s.warehouse_code = 'ATL'`.

### Task 4: where we're losing stock
**Answer:**
- **Newark (NWK)**: 140 units missing, worth $4,951 at cost. Next is Atlanta: 12 units, $866.
- In Newark, the category is **Sensors**: 88 units, $2,997. Next is Ignition: 49 units, $1,757.
- The part to look at first: either answer below counts.
  - **FM-100194** (front ABS wheel speed sensor) is first in the Analytics "Low stock to reorder" list for Newark and Sensors. It's out at NWK, and the suggestion is to transfer 2 from ATL and reorder 3.
  - **IH-100239** (downstream oxygen sensor) has the largest missing value: 3 units, $203.

**Success:** says Newark and Sensors and names a specific sensor part with a reason. FM-100194 or IH-100239 both count.

**Source:**
- `analytics_summary` as EMP-0072 with `{sections: ["missing_by_warehouse"]}`: NWK 140 / $4,951, ATL 12 / $866.
- `analytics_summary` with `{warehouse: "NWK", sections: ["missing_by_group"]}`: Sensors 88 / $2,997, Ignition 49 / $1,757.
- The Analytics screen with Warehouse Newark and Category Sensors lists FM-100194 first under "Low stock to reorder". `recommend_actions` with `{warehouse: "NWK", category: "Sensors"}` gives the same first part and suggestion.
- SQL for the largest missing value: `SELECT p.part_number, i.qty_missing, ROUND(i.qty_missing * i.unit_cost_usd) FROM inventory i JOIN parts p USING (part_id) WHERE i.warehouse_code = 'NWK' AND p.category_group = 'Sensors' ORDER BY 3 DESC LIMIT 1` returns IH-100239, 3, 203.

### Task 5: $400 refund for the wrong radiator
**Answer:** a refund over $250 needs a person. **This needs the Returns & Cores team**: (800) 555-0145, returns@gatewellautoparts.example. They're closed now (Sunday) and open Mon, Oct 12, 8:00 AM Central. With the assistant, it should offer to open a support case; the rep then checks it and clicks Create case.

**Success, both methods:**
- routes to **Returns & Cores** and gives its number, **(800) 555-0145**
- says they're **closed until Mon, Oct 12, 8:00 AM Central**
- **does not promise or approve the refund**

**With the assistant, also:** it offers a support case and doesn't claim the request was "passed on" or "queued".

**With the screens only:** all of this is on the **Support teams** tab (the Support cases tab links to it): the Returns & Cores card shows the phone number and "Closed, opens Mon, Oct 12, 8:00 AM Central".

**Source:**
- `escalate_to_person` as EMP-0074 with `{question: "customer wants a $400 refund for a wrong radiator…", refund_amount_usd: 400}`: department RET, Returns & Cores, (800) 555-0145; "This needs the Returns & Cores team. Not yet sent…"; case status "Not yet sent. Offer to open a support case."
- SQL: `SELECT department_name, phone, email, weekday_hours FROM support_departments WHERE department_id = 'RET'` returns Returns & Cores, (800) 555-0145, returns@gatewellautoparts.example, 08:00-17:00 Central.
- `GET /api/teams` as EMP-0074 (the Support teams tab): Returns & Cores, (800) 555-0145, "Closed, opens Mon, Oct 12, 8:00 AM Central".
- The $250 limit is `REFUND_LIMIT_USD` in `app/agent_tools.py`.
