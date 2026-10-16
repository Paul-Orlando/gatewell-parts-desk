# Fictional names plan: no real brands anywhere

**Goal:** no real company, vehicle, engine or carrier name appears anywhere in the data, app, prompts, tests or docs. The numbers stay exactly the same: quantities, orders, shipments, rates and the planted scenarios. Only names change.

**When:** do this right after the retest polish is committed, and **before Phase A** of `docs/EVIDENCE_PLAN.md`. Every later phase then uses the new names.

---

## 0. Instructions for Claude Code (read first)

Use plan mode. Before regenerating anything, create `data_generator/name_map.py` with the makes and carriers from this plan plus your proposed fictional model names, and show the full map to the user for approval.

**Key rules:**
- Names change only in a final translation step before the tables are written. The generation logic and random draws stay untouched.
- Prove it: compare the old and new databases table by table and show the user that only name and part-number text changed.
- Carrier rules, limits, surcharges and rates stay identical under the new names.
- Never loosen a permission test.
- Put the up-front line, "Vehicles and carriers are fictional equivalents of common U.S. models and major parcel carriers.", in every place listed in section 9.

**When done:**
- Run the full test suite.
- Start the app and check the screens at desktop and phone width, including the up-front line on the sign-in page.
- Confirm the planted scenarios from section 10 under their new names.
- Commit as "Replace all real brand, vehicle and carrier names with fictional ones". Don't push.

---

## 1. How to change names without changing the data

Don't rename inside the generation logic. Renaming changes sort orders, and sort orders change the random draws, so every number would shift.

- **Generation stays as is.** It keeps using today's internal names and keys.
- **Names change at the very end.** Add one translation step in `generate_dataset.py`, right before the tables are written. It replaces every name using a single map file: `data_generator/name_map.py`.
- **Part numbers change in the same final step.** OEM part numbers use the real car makers' formats, so map each one to a neutral number. Number them in `part_id` order, for example `FM-100123` with a two-letter prefix per make. Apply the same mapping everywhere a part number appears: parts, interchange, order and shipment lines, cases, and anything else.
- **Aftermarket part numbers stay.** They already use our fictional prefixes (KT-, TY-, CV- and so on).
- **Proof:** compare the old and new databases table by table. Every row and every number must match; only name and part-number text may differ. Report the comparison.

## 2. Vehicle makes (proposed; I'll confirm or change)

| Real | Fictional | Group (internal family code) |
|---|---|---|
| Ford | Halvard | HAL |
| Chevrolet | Castellan | CAS |
| GMC | Castellan Pro | CAS |
| Ram | Ironhorn | IRN |
| Jeep | Tralon | IRN |
| Dodge | Vexley | IRN |
| Chrysler | Ambrel | IRN |
| Toyota | Kenzai | KEN |
| Honda | Ferra Motors | FER |
| Nissan | Sorano | SOR |
| Hyundai | Daeyon | DAE |
| Kia | Hanvel | DAE |
| Subaru | Aokiri | AOK |
| Tesla | Voltrane | VOL |

- **Internal codes:** the family codes (FORD, GM, STLA, TOY, HON, NIS, HK, SUB, TES) also get replaced wherever they reach the database, the API or the interface, such as engine codes. Code-only constants can keep the old keys if they never leave the generator, but the new codes are preferred.
- **OEM brand label:** "<Fictional make> OEM", for example "Ferra Motors OEM". Brand type and quality tier stay "OEM".

## 3. Models

Claude Code proposes one fictional model name for every model in `VEHICLE_DEFS` and puts them in `name_map.py` for my review **before** regenerating. Rules:
- Invented, pronounceable names that aren't a real vehicle model from any maker. Avoid real model names, including common words used as models (Edge, Focus, Pilot, Ranger, Frontier, Compass, Charger, Outback, Forte, Pathfinder, and so on).
- Keep the body type, years, engines and popularity exactly as they are.
- Plain numbers for heavy-duty trims are fine (1500, 2500). Don't copy real letter-and-number names (F-150, CR-V, RAV4, HR-V, Model 3, Model Y, 4Runner).
- Choose names that hint at the vehicle type, so people recognize it quickly. A full-size pickup should sound rugged, a compact car light, a minivan family-friendly, and an EV electric.

## 4. Engines

Drop trade names (EcoBoost, Pentastar, HEMI) and any maker reference (Cummins). Use generic descriptions, for example:
- "2.7L V6 Twin-Turbo"
- "5.7L V8"
- "6.7L I6 Turbo Diesel"

## 5. Parcel carriers

| Real | Fictional | Code prefix |
|---|---|---|
| UPS | Parcelora | PCL |
| FedEx | Velocair | VLC |
| USPS | Postara (national postal service) | PST |
| DHL | Globexa Express | GBX |

- **Service names and codes follow the new names.** For example, "Parcelora Ground" `PCL_GND`, "Velocair 2Day" `VLC_2D`, "Postara Priority" `PST_PRI`, "Globexa Express Worldwide" `GBX_EXW`. Rename service names that echo real products ("Ground Advantage", "Priority Mail Express", "Worldwide Saver") to plain descriptions, such as "Postara Ground Saver" and "Postara Priority Overnight".
- **Everything else stays identical:** each carrier's rules, limits, surcharges, transit times and rates (for example, the postal service's 70 lb limit and no lead-acid batteries).
- Freight forwarders, ocean and truck carriers, and "Gatewell Delivery" are already fictional and stay.

## 6. What stays real

Countries, states, cities, ports, border crossings, time zones, currencies, exchange-rate behavior and HS customs codes. These are places and public facts, not brands.

## 7. Update everything that uses the old names

- **App:** `app/` (services, agent_tools, assistant system prompt and tool descriptions, analytics), `app/static/` (placeholders, examples, labels) and the FAQ text.
- **Tests:** update expected names and part numbers using the map. Never loosen a permission test.
- **Docs:** `README.md`, `docs/` (ARCHITECTURE, DATA_DICTIONARY, NEXT_STEPS, GUARDRAILS_PROPOSAL, EVIDENCE_PLAN including the user-test tasks and demo beats, and both test reports). In the two test reports, rewrite the names using the map and add a line at the top: "Names updated to fictional equivalents on <date>; numbers unchanged."
- **Name map document:** add `docs/NAME_MAP.md` listing old and new names. It is for maintainers only and is the one place old names may appear. Add a line at its top: "Internal reference for maintainers; not shown in the app."

## 8. Guard against old names coming back

Add `tests/test_no_real_brands.py`:
- Every make, model, brand, engine and carrier name in the database comes from `name_map.py`'s fictional set.
- Scan `app/`, `app/static/` and the database text columns for a denylist of the real makes, carrier names and engine trade names (whole words, case-sensitive). There must be no matches. `docs/NAME_MAP.md` is excluded.

## 9. Notice and CLAUDE.md

- **Notice:** in the README, the Data Dictionary and the sign-in page footer: "Gatewell Auto Parts and all companies, vehicles, brands, carriers, people, orders, prices and rates in this demo are fictional. Any resemblance to real products or companies is coincidental. Place names and currencies are real."
- **Say it up front.** Use this exact line wherever the project is presented: "Vehicles and carriers are fictional equivalents of common U.S. models and major parcel carriers."
  - **Sign-in page:** under the lead text, above the role cards, in small muted text.
  - **README.md:** in the "Capstone prototype" note at the top.
  - **`docs/EVIDENCE_PLAN.md`, Phase D:** the demo script's 0:00 beat must say this line aloud while the role cards are on screen. Add it to the script's opening narration.
  - **`docs/user_test/script.md`** (when it's created in Phase C): in the facilitator's intro.
  - **Design-decisions paper:** if a Markdown copy exists in the project or its parent folder (`Gatewell_Parts_Desk`), add the line to its Data section and update any real names using the map. The published online version is updated separately.
- **CLAUDE.md, Interface design section:** "Names: all vehicle makes, models, brands and carriers are fictional (see data_generator/name_map.py). Never add real company, vehicle, engine or carrier names, logos or styling."

## 10. Done when

- the database comparison shows only name and part-number text changed
- the full test suite passes, including the new brand test
- the app runs and screens show the new names at desktop and phone width
- the "fictional equivalents" line shows on the sign-in page and appears in the README and the demo script
- the planted scenarios still hold under their new names: the Atlanta backorder (0 available, 11 backordered, 120 inbound, ETA Oct 14), Newark shrinkage (140 units, $4,951), 5 Ningbo customs holds, winter battery transfers, and MXN 19.57 to 21.31
- one commit: "Replace all real brand, vehicle and carrier names with fictional ones". Don't push.
