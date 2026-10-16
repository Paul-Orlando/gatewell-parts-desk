# Gatewell Parts Desk

An internal web app for **Gatewell Auto Parts Co.**, a fictional U.S. distributor of OEM and aftermarket car parts with 11 warehouses and customers at home and abroad.

Customer service agents, warehouse staff and managers use it to:
- check inventory
- look up orders
- quote parts and shipping with every major carrier
- work support cases
- see analytics
- ask an AI assistant about any of the above

**Stack:**
- **Backend:** Python (FastAPI) with a SQLite database.
- **Frontend:** plain HTML, CSS and JavaScript, with no build step.
- **Assistant:** Gemini 3.1 Flash-Lite through OpenRouter.
- **Hosting:** Railway.

> **Capstone prototype.** Vehicles and carriers are fictional equivalents of common U.S. models and major parcel carriers. All data is synthetic and royalty-free; see `docs/DATA_DICTIONARY.md`. Shipping and exchange rates are realistic estimates, not live carrier or bank rates. This is a **demo version**: the assistant answers 5 questions per visitor.
>
> Gatewell Auto Parts and all companies, vehicles, brands, carriers, people, orders, prices and rates in this demo are fictional. Any resemblance to real products or companies is coincidental. Place names and currencies are real.

## What's inside

| Tab | Who sees it | What it does |
|---|---|---|
| **Inventory** | Everyone | Search parts by number, name, brand or vehicle (year/make/model). See stock in every bucket at every warehouse: available, reserved, damaged, missing, in transit, backordered. The part view adds bin locations, inbound shipments, fitment, equivalent parts, and a **shipping quote** from Parcelora, Velocair, Postara and Globexa Express. |
| **Orders** | Everyone (warehouse staff see only their warehouse) | Find orders by number, customer, tracking number or part. See lines with bins, carrier and tracking, customs and export documents, currency, import tax and payment. |
| **Assistant** | Everyone | Ask questions in plain English, 5 per visitor in the demo. It looks up answers with the same tools the screens use, limited to what your role may see. When it can't answer, it hands off to the right team with phone, email, hours and FAQ links. |
| **Support cases** | Customer service, supervisors, managers | Open and resolved customer contacts, including handoffs from the chat. |
| **Support teams** | Everyone | Read-only directory of the support teams: what each handles, phone, email, hours (Central), languages, and whether it's open now. |
| **Analytics** | Customer service supervisors, managers | Inventory levels and value, low and missing stock, stock age, prices by category, sales by month, region and country, shipping cost vs. charged by carrier, and exchange gains and losses. |

### Roles

| Role | Job titles | Sees costs and margins | Sees prices and payments | Sees customer names | Data scope |
|---|---|---|---|---|---|
| Warehouse | Warehouse Associate, Inventory Control Specialist | No | No (list price only) | No | Their warehouse's orders |
| Customer Service | Customer Service Rep | No | Yes | Yes | Company-wide |
| CS Supervisor | Customer Service Supervisor | No | Yes | Yes | Company-wide, plus analytics |
| Management | Warehouse Manager, Regional Manager, Purchasing Analyst, Operations Director | Yes | Yes | Yes | Their warehouse, region, or company-wide |

All permission checks run on the server. The browser only hides tabs a role can't use.

## Run it on your computer

You need **Python 3.11+**. The assistant needs an **OpenRouter API key**; every other tab works without one.

**Mac or Linux**
```bash
cd gatewell_app
cp .env.example .env          # then put your OPENROUTER_API_KEY in .env
./run.sh
```

**Windows**
```bat
cd gatewell_app
copy .env.example .env        & rem then put your OPENROUTER_API_KEY in .env
run.bat
```

Open **http://localhost:8000** and choose an employee to sign in as. Some good ones to try:
- **Operations Director:** everything, company-wide.
- **Warehouse Manager (Atlanta):** analytics for one warehouse.
- **Customer Service Rep:** quotes, orders, cases.
- **Warehouse Associate (Atlanta):** bins and stock only.

The sample data is a snapshot taken **Sunday, Oct 11, 2026, 4:00 PM Central**. That's why support teams show as closed.

### Settings (`.env` locally, Variables on Railway)

| Setting | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | (none) | Turns on the assistant |
| `GATEWELL_MODEL` | `google/gemini-3.1-flash-lite` | Model the assistant uses (any OpenRouter model with tool calling) |
| `GATEWELL_TEMPERATURE` | `0.1` | Low for consistent, factual answers |
| `GATEWELL_DEMO_MODE` | `1` | Demo version on (`1`) or off (`0`) |
| `GATEWELL_DEMO_CHAT_LIMIT` | `5` | Assistant questions per visitor in the demo |
| `GATEWELL_DEMO_IP_LIMIT` | `25` | Backstop per network address, so clearing cookies doesn't reset the limit |
| `GATEWELL_DEMO_CASE_LIMIT` | `3` | Support cases per visitor in the demo |
| `GATEWELL_DEMO_CASES_PER_DAY` | `50` | Support cases per day for all visitors together |
| `GATEWELL_DB` | `data/car_parts_inventory.db` | Database file. On Railway, use the volume, e.g. `/data/car_parts_inventory.db` |
| `GATEWELL_LOG_DIR` | `logs/` | Assistant audit log and demo counts. On Railway, use `/data/logs` |
| `GATEWELL_AS_OF` | `2026-10-11T21:00:00Z` | "Now" for the snapshot, or `now` for live data |

## Deploy to Railway

**`docs/DEPLOY.md`** is the full guide: the exact Variables, the `/data` volume, the `/api/health` health check, what's logged, and how to reset the demo data and counters.

> **Before going public with real data:** the prototype's pick-an-employee sign-in lets anyone act as any employee. That's fine for the demo's synthetic data only. Add company sign-on first; see `docs/NEXT_STEPS.md`, step 5.

## Test it

```bash
pip install -r requirements.txt
python -m pytest tests
```

There are 231 tests. They run against a throwaway copy of the database and need no API key, because a scripted stand-in replaces the model. They cover:
- **Permissions:** what every role can and can't see, and data-scope limits.
- **The assistant's tool loop:** tool access by role, redaction, request settings, malformed tool calls, escalation, the loop limit, audit logging, and OpenRouter error handling.
- **The demo limits:** 5 questions per visitor, not reset by switching employees, failures don't count, a backstop per network address; 3 support cases per visitor and 50 per day; on unless explicitly switched off.
- **Business rules:** batteries ground-only and not overseas, Postara size limits, no free shipping on oversize parts, currency and tax totals, after-hours handoff, and a read-only database.
- **Deployment:** the health check (503 when the database can't be read), security headers, the first-start database copy, and log folders created on a fresh volume.

## Evaluate the assistant

The evaluation asks the real model 50 graded questions (`tests/eval/questions.yaml`) as the employees in the file, and scores facts, tool choice, handoffs and refusals. It costs money, so it isn't part of `pytest`. `tests/test_eval_set.py` checks the questions' expected answers against the data for free.

On Windows, `eval.bat` runs it with the key from `.env`, the same way `run.bat` starts the app. It never prints the key, and any arguments pass through:

```
eval.bat --limit 3 --runs 1      # smoke test: 3 questions, 1 run each (about $0.01)
eval.bat                         # all 50 questions, 3 runs each (about $0.35-0.45)
eval.bat --group restricted      # one group; also --only ID..., --model, --price-in, --price-out
```

Results go to `tests/eval/results/<date>_<model>.csv` (one row per run) and `.md` (pass rates, consistency, refusal accuracy, time, cost, and every failure with the answer given). See `docs/EVIDENCE_PLAN.md`, Phase B.

When a scoring rule changes, re-grade saved answers without calling the model: `.venv\Scripts\python tests\eval\run_eval.py --rescore tests\eval\results\<file>.csv` writes `<file>_rescored.csv` and `.md`. Every scoring change and its reason is logged in `tests/eval/SCORING_CHANGES.md`.

## Project layout

```
gatewell_app/
  app/
    server.py        web server, API, health check, security headers (FastAPI)
    auth.py          roles, permissions, data scope, field redaction
    services.py      inventory, orders, cases queries shared by screens and assistant
    analytics.py     analytics queries
    recommend.py     suggested actions (transfers, reorders, substitutes); read-only
    assistant.py     model tool loop (OpenRouter), system prompt, tools per role, audit log
    agent_tools.py   pricing, shipping rate engine, FAQ, live-person handoff
    demo.py          demo limit: 5 assistant questions per visitor
    db.py            read-only database access; first-start copy onto the volume
    static/          the web app (HTML, CSS, JavaScript); brand/ holds the piston logo; vendor/ holds Chart.js and fonts
  data/              SQLite database (synthetic)
  data_generator/    script that rebuilds the dataset from a fixed seed
  docs/
    NEXT_STEPS.md         how to continue in VS Code with Claude Code
    GUARDRAILS_PROPOSAL.md rules for the assistant, for review
    ARCHITECTURE.md       how it fits together
    DATA_DICTIONARY.md    every table and column
  tests/
  CLAUDE.md          project rules Claude Code follows
  .claude/           Claude Code permission settings
  Procfile           start command for Railway
```

## Rebuild the data

```bash
cd data_generator
python generate_dataset.py          # about 15 seconds; identical data on every run (about 43 MB)
mv car_parts_inventory.db ../data/
```

## Known limits of the prototype

- **Sign-in:** you pick an employee from a list. Add company sign-on before any public deployment.
- **Live data:** the data is a synthetic snapshot. A real deployment connects the warehouse and ERP systems, carrier rating APIs, and a daily exchange-rate feed.
- **Assistant memory:** the assistant only remembers the current conversation in the browser tab.
- **Write access:** by design, the assistant can't change inventory, orders, prices or refunds.

## Credits and licenses

- **Fonts:** Public Sans and Barlow Semi Condensed, under the SIL Open Font License.
- **Charts:** Chart.js, under the MIT license.
- **Logo and data:** the piston logo is original. Company, people, part numbers and prices are fictional. Vehicle names are trademarks of their owners.
