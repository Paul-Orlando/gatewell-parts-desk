# Next steps: continuing in VS Code with Claude Code

This guide takes the project from the delivered prototype to a deployed demo on Railway. Each step has a prompt you can paste into Claude Code. Claude Code reads `CLAUDE.md` automatically, so it already knows the project's security rules and design rules.

## Where things stand

| Area | Status |
|---|---|
| Inventory, Orders, Support cases, Analytics tabs | Done; tested in a browser for all six roles |
| Assistant (Gemini 3.1 Flash-Lite via OpenRouter) | Done; tested end to end against a stand-in for OpenRouter. **Not yet tried with your real key.** |
| Roles, redaction, data scope, read-only database | Done; tested |
| Demo limit (5 questions per visitor) | Done; tested |
| Shipping quotes (UPS, FedEx, USPS, DHL), currencies, import tax | Done; tested |
| Railway readiness: health check, security headers, volume copy, `Procfile` | Done; tested |
| Logo and design rules | Done |
| **Company sign-on** | **Not started. Required before a public deploy.** |
| Evaluation set, grounding check, feedback buttons, rate limit | Not started (see the guardrails proposal) |

There are 37 automated tests, and all pass from a clean install.

---

## Step 0: Set up (once)

1. **Install** VS Code, Python 3.11 or newer, and Git. Then install the **Claude Code** extension from the VS Code Extensions panel.
2. **Unzip** `gatewell_parts_desk.zip`. In VS Code, choose **File → Open Folder** and select `gatewell_app`.
3. **Put the project in Git and GitHub** (private repository), from VS Code's terminal:
   ```bash
   git init
   git add .
   git commit -m "Gatewell Parts Desk prototype"
   ```
   Then create a private repository on GitHub and push to it. VS Code's Source Control panel can publish it for you.
4. **Add your key.** Copy `.env.example` to `.env` and paste your OpenRouter key after `OPENROUTER_API_KEY=`. `.env` is in `.gitignore`, so it won't be committed, and Claude Code is blocked from reading it.
5. **Run it.** Use `./run.sh` (Mac/Linux) or `run.bat` (Windows), then open http://localhost:8000.
6. **Run the tests.** Use `python -m pytest tests`. You should see 37 passed.

**Working habits with Claude Code:**
- **One task per conversation.** Paste one step's prompt, review what it plans, then let it work.
- **Use plan mode for anything touching security:** `auth.py`, `assistant.py`, `db.py`, the system prompt, or sign-on. Read the plan before approving.
- **Review the diff before accepting.** Ask Claude Code to run the tests and to show a screenshot for interface changes.
- **Commit after each step** that works, so you can always go back.
- **Testing the demo limit locally:** set `GATEWELL_DEMO_MODE=0` in `.env`, or delete `logs/demo_usage.db` to reset the counts.

---

## Step 1: Try the assistant with your real key

Open the Assistant tab and ask 10 to 15 real questions across roles. Note anything wrong: a wrong tool, a guessed number, a missed handoff, or a slow reply.

> **Prompt:** "I tested the assistant with Gemini 3.1 Flash-Lite and saw these problems: [paste examples]. Read `logs/assistant_audit.jsonl` for those questions and explain what went wrong for each one: prompt, tool choice, or tool data. Propose fixes, but don't change `auth.py` or the tool roles."

## Step 2: Build an evaluation set

This is the most important quality step. Run it before any later change to the model, prompt or tools.

> **Prompt:** "Create `tests/eval/questions.yaml` with 50 realistic employee questions across all roles. Cover stock and fitment, orders, shipping quotes, currency and import tax, restricted data (e.g. a warehouse associate asking for costs), and handoffs. Give each one the expected facts, taken from the database, and the expected tool. Then write `tests/eval/run_eval.py`, which runs them against the live model through `assistant.chat()`. It should report pass/fail per question, the accuracy, and the cost from token counts. Keep it out of the normal pytest run, since it calls the real API."

## Step 3: Tune the prompt for Flash-Lite

> **Prompt:** "Using the eval results, tighten `system_prompt()` in `app/assistant.py` for Gemini 3.1 Flash-Lite. Make it shorter and more direct. Add three or four short worked examples of correct tool use, including one where it should ask a follow-up question (which engine) and one where it should hand off. Keep every existing rule. Rerun the eval and show before and after accuracy."

## Step 4: Add the grounding check

> **Prompt:** "Add a grounding check to `assistant.chat()`, as guardrail B9 in `docs/GUARDRAILS_PROPOSAL.md` describes. Before returning a reply, extract every dollar amount and quantity in it and confirm each appears in a tool result from that turn. If any don't, retry once, asking the model to use only tool data. If it still fails, append a short warning to the reply. Log failures in the audit log. Add tests with the stand-in model in `tests/test_assistant.py`."

## Step 5: Company sign-on (required before a public deploy)

First decide which provider: Google Workspace or Microsoft Entra ID.

> **Prompt (plan mode):** "Replace the prototype pick-an-employee sign-in with [Google Workspace / Microsoft Entra ID] sign-on using OpenID Connect. Map each signed-in email to an employee in the `employees` table: add an `email` column, and generate sample emails at `@gatewellautoparts.example` in the data generator. Keep `current_employee()` as the single place identity is decided, and replace the `X-Employee-Id` header with a signed session cookie. Keep the pick-an-employee screen only when `GATEWELL_DEMO_SIGNIN=1`, for local demos, and make it impossible to enable on Railway unless explicitly set. Update the permission tests so they still pass. Explain the security impact."

For a quick public demo without sign-on, put the Railway URL behind an access gateway that only admits listed email addresses (for example Cloudflare Access), and keep the pick-an-employee screen behind it.

## Step 6: Deploy to Railway

Follow **Deploy to Railway** in `README.md`:
1. Deploy from the GitHub repo.
2. Add a volume at `/data`.
3. Set the variables `OPENROUTER_API_KEY`, `GATEWELL_DB=/data/car_parts_inventory.db` and `GATEWELL_LOG_DIR=/data/logs`.
4. Set the health check path to `/api/health`.
5. Generate a domain.

Use a **staging** environment first.

> **Prompt:** "Add a GitHub Actions workflow that runs `python -m pytest tests` on every pull request and on pushes to `main`. Explain how to turn on branch protection, so `main` only accepts pull requests whose tests pass and Railway only deploys tested code."

## Step 7: Interface polish

> **Prompt:** "Review the interface against the 'Interface design' rules in `CLAUDE.md`. Suggest five improvements for warehouse staff on a tablet and customer service at a desk, for example larger touch targets on the Inventory tab, and keyboard shortcuts for search. Implement the ones I approve. Take screenshots before and after in light and dark mode at 1440px and 390px width."

## Step 8: Feedback and rate limits

> **Prompt:** "Add thumbs up/down buttons with an optional comment under each assistant answer. Store them with the audit entry. Add a per-employee rate limit of 60 assistant questions per hour, on top of the demo limit. Then add a small 'Assistant quality' panel to the Analytics tab for managers: questions per day, handoff rate, thumbs-down rate. Add tests."

## Step 9: Capstone write-up

> **Prompt:** "Using `docs/ARCHITECTURE.md`, `docs/GUARDRAILS_PROPOSAL.md` and the eval results, draft a capstone report with these sections: problem, users and roles, architecture (model, harness and tools; why direct tool calls instead of MCP; model-agnostic design), guardrails, testing and evaluation, results, limitations, and next steps. Include the screenshots and a role-permission table."

---

## Decisions still open (from the guardrails proposal)

1. **Sign-on provider:** Google Workspace, Microsoft Entra ID, or an access gateway for the demo.
2. **Refund handoff threshold:** $250 as built.
3. **Price visibility:** can warehouse staff see customer prices, and can customer service see our costs?
4. **Assistant actions:** read-only plus support cases, or confirmed actions later?
5. **Audit log retention** and who can read it.
6. **Assistant owner.**

---

## File map

| File or folder | What it's for | Change it when |
|---|---|---|
| `CLAUDE.md` | Rules Claude Code follows: security, tools, design | Your team's rules change |
| `.claude/settings.json` | Claude Code permissions (no `.env` reads; ask before push/deploy) | You want different permissions |
| `app/server.py` | Web routes, demo cookie, health check, security headers | Adding screens or API endpoints |
| `app/auth.py` | Roles, permissions, data scope, redaction | Only with plan mode and tests (sign-on goes here) |
| `app/assistant.py` | Model calls (OpenRouter), system prompt, tool list, audit log | Prompt tuning, grounding check, new tools |
| `app/agent_tools.py` | Prices, shipping rate engine, FAQ, handoff rules | Business rules change, or connecting carrier APIs |
| `app/services.py`, `app/analytics.py` | Data queries for screens and assistant | New lookups or reports |
| `app/demo.py` | Demo limit | Changing demo behavior |
| `app/db.py` | Read-only database access, volume copy | Moving to Postgres |
| `app/static/` | The interface; `brand/` holds the logo | Interface work |
| `data/` | Synthetic database | Regenerate with `data_generator/` |
| `tests/` | 37 automated tests | Every change adds or updates tests |
| `docs/` | Architecture, guardrails, data dictionary, this guide | Keep them in step with the code |
| `.env.example` | Setting names, no values | Adding a setting |
| `Procfile` | Railway start command | Rarely |

## Troubleshooting

- **"The assistant needs an OpenRouter API key"** means `OPENROUTER_API_KEY` isn't set. Restart after editing `.env`.
- **"The assistant is unavailable right now (…)"** means OpenRouter returned an error; the reason is in the brackets. Check the key, your account's credit and limits, and the model name.
- **The demo limit was reached while testing:** set `GATEWELL_DEMO_MODE=0`, or delete `logs/demo_usage.db` locally.
- **Support teams always show as closed:** that's the Sunday-afternoon data snapshot. Set `GATEWELL_AS_OF=now` with live data.
- **Railway lost cases or logs after a redeploy:** the volume isn't mounted at `/data`, or the `GATEWELL_DB` and `GATEWELL_LOG_DIR` variables don't point at it.
