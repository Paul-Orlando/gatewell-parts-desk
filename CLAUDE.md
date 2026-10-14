# Gatewell Parts Desk — rules for Claude Code

Internal employee app for Gatewell Auto Parts Co. FastAPI backend (`app/`), plain-JS frontend (`app/static/`), SQLite data (`data/`), AI assistant using Gemini 3.1 Flash-Lite via OpenRouter. Deployed on Railway.

## Never weaken these (security-critical)
- **Sign-in and roles** (`app/auth.py`): every API route depends on `current_employee`. Never add a route without it, except `/api/health` and sign-in.
- **Redaction:** everything returned to the browser or to the model passes through `auth.redact(..., emp)`. Never return raw query results. Redaction is an allowlist: every field name must be classified in `auth.py` (public, cost, money or customer). An unclassified field is hidden from restricted roles, and `test_every_returned_field_is_classified` fails until you classify it. Never classify a price, cost or customer detail as public.
- **Data scope:** queries on orders and analytics use `auth.scope_sql`. Never let a request parameter widen an employee's scope.
- **Read-only database:** lookups use `db.read_conn()`. The only write path is `db.write_support_case` / `agent_tools.create_support_case`, reached from the chat only through `POST /api/cases/confirm` after the employee clicks Create case (the assistant's `propose_support_case` saves nothing). Don't add new writes without explicit approval from the user.
- **Assistant limits** (`app/assistant.py`): keep the role-based tool list, the round limit, result size cap and audit log. Don't remove or loosen them.
- **Demo limit** (`app/demo.py`): the demo allows 5 assistant questions per visitor, counted on the server. Don't move the check to the browser or remove it; switch it off only with `GATEWELL_DEMO_MODE=0`.
- **Business rules** in `app/agent_tools.py` (battery shipping, carrier limits, free-shipping rules) are company policy. Change only when asked.

## When adding or changing an assistant tool
1. Implement the logic in `services.py` or `agent_tools.py` (shared with the screens), not in the prompt.
2. Register it in `assistant.TOOLS` with the narrowest `roles` that need it.
3. Make sure its result goes through `run_tool` (role check + redaction + size cap).
4. Add tests in `tests/`, including one proving a role that shouldn't have it can't use it.

## Model provider
- All model-provider code stays inside `app/assistant.py`. Nothing else imports a model SDK.
- Model and provider come from environment variables (`GATEWELL_MODEL`, `OPENROUTER_API_KEY`). Never hard-code keys.
- OpenRouter requests send `provider: {"require_parameters": true}` so they only go to providers that support tool calls. Spending limits and privacy settings are managed in the OpenRouter account, not in code.

## Secrets and data
- Never read, print, or commit `.env` or any API key. Use `.env.example` for placeholders.
- Data in `data/` is synthetic. Don't add real customer data to the repository.

## Before saying a change is done
- Run `python -m pytest tests` and make sure everything passes.
- Never delete or loosen tests in `tests/test_permissions.py` to make a change pass. If a permission test fails, the change is wrong.
- For changes to `auth.py`, `assistant.py`, `db.py` or the system prompt, explain the security impact in the summary.

## Style
- Plain, readable Python with short docstrings. Plain JavaScript (no build step). Keep user-facing text in plain, sentence-case English.

## Interface design (clean and professional)
- **Logo:** the Gatewell piston in `app/static/brand/`. `piston-mark.svg` uses `currentColor` (navy on light, white on dark) with a fixed amber top ring; inline it so the color follows. Use `favicon.svg` / `app-icon-512.png` for small sizes and app icons. Don't recolor the amber ring, stretch, rotate, outline or add effects to the logo.
- **Colors:** use the CSS tokens in `styles.css` (`--ink` navy, `--bg` steel grey, `--accent` blue for actions and links, amber `--warn-mark` only for attention and the logo ring). Never hard-code new colors; add a token for both light and dark themes.
- **Type:** Barlow Semi Condensed for headings, part numbers, bins and big figures; Public Sans for everything else. Both are bundled in `static/vendor/fonts`. No other fonts.
- **Status:** always an icon plus a word (In stock, Low, Out, Inbound). Never color alone.
- **Layout:** dense, scannable tables for data work; the detail drawer for one record; filters in one row above results. Keep it quiet: no gradients, decorative shadows or animations beyond opening and closing panels.
- **Quality floor:** works at phone width, keyboard focus visible, dark mode via the existing tokens, text contrast at least 4.5:1. Check changes with a screenshot before calling them done.
