# Deploying the public demo on Railway

The public demo runs the app as-is on Railway, with synthetic data and the demo limits on. Anyone with the link can sign in as any sample employee; that's deliberate for the demo, and safe only because every record is fictional. A real deployment needs company sign-on first (`docs/NEXT_STEPS.md`, step 5).

## 1. Service

1. In Railway, choose **New Project**, then **Deploy from GitHub repo**, and pick this repository.
2. **Start command:** Railway reads it from the `Procfile`. Don't override it.

   ```
   web: uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8000}
   ```

3. **Volume:** add a volume to the service, mounted at **`/data`**. The database and logs live there, so they survive redeploys.
4. **Health check:** in the service settings, set the health check path to **`/api/health`**.
   - It needs no sign-in.
   - It returns `{"ok": true}` (200) when the database can be read, and `{"ok": false}` (503) when it can't, so a bad deploy fails instead of going live.
5. **Domain:** under Networking, generate a domain.

## 2. Variables

Set these under the service's **Variables** tab, exactly as written:

| Variable | Value | Why |
|---|---|---|
| `OPENROUTER_API_KEY` | your OpenRouter key | Turns on the assistant. Enter it in Railway only; never put it in the repository, `.env.example` or a commit. |
| `GATEWELL_MODEL` | `google/gemini-3.1-flash-lite` | The model the assistant uses |
| `GATEWELL_DEMO_MODE` | `1` | Demo limits on. A missing or empty value also means on; only `0`, `false`, `no` or `off` turns them off. |
| `GATEWELL_DB` | `/data/car_parts_inventory.db` | The database on the volume |
| `GATEWELL_LOG_DIR` | `/data/logs` | Audit log and demo counts on the volume |

These are optional. Leave them unset to keep the defaults:

| Variable | Default | What it limits |
|---|---|---|
| `GATEWELL_DEMO_CHAT_LIMIT` | `5` | Assistant questions per visitor |
| `GATEWELL_DEMO_IP_LIMIT` | `25` | Assistant questions per network address (a backstop against clearing cookies) |
| `GATEWELL_DEMO_CASE_LIMIT` | `3` | Support cases per visitor |
| `GATEWELL_DEMO_CASES_PER_DAY` | `50` | Support cases per day for all visitors together (days in Central time) |

**Before going public:** set a monthly spending limit on the OpenRouter key in your OpenRouter account. The demo limits cap use per visitor; the spending limit caps the total.

## 3. First start

On the first start the volume is empty, so the app copies the bundled sample database to `/data/car_parts_inventory.db`. After that it never overwrites it.

`/data/logs/` is created the first time it's needed. It holds:
- `assistant_audit.jsonl`: one line per assistant question. It records the employee ID, role, question, tools used, tokens and time, but not the answer.
- `demo_usage.db`: the counts for the demo limits.

**Check it:**
- Open `https://<your-domain>/api/health`. It should show `{"ok":true}`.
- Sign in as a Customer Service Rep and ask the assistant a question; the reply should count down your questions.

## 4. What's logged

The sign-in page says: "Demo questions are logged to improve the app. Don't enter personal information." The audit log holds each question's text. Download it from the volume to review it, and delete it when you no longer need it.

## 5. Resetting the demo

Open the service's shell in Railway (the service's **⋯** menu, or `railway ssh` with the Railway CLI), then:

| To reset | Run | Then |
|---|---|---|
| **Demo data** (support cases visitors created) | `rm /data/car_parts_inventory.db` | Restart the service. The bundled database is copied back on start. |
| **Demo counters** (questions and cases per visitor and per day) | `rm /data/logs/demo_usage.db` | Nothing; it's recreated on the next request. |
| **Audit log** | `rm /data/logs/assistant_audit.jsonl` | Nothing; download it first if you want to keep it. |

Resetting the data doesn't reset the counters, and resetting the counters doesn't reset the data, so do both for a clean start.

New deploys don't reset anything on the volume. To ship a regenerated sample database, deploy it, then reset the demo data as above.

## 6. Switching the demo off

To run without limits (for example, an internal test), set `GATEWELL_DEMO_MODE=0`. Never do this on the public link: it removes the question and case limits.
