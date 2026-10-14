# Start here: Gatewell Parts Desk in VS Code with Claude Code (Windows)

## 1. Open the right folder

In VS Code, choose **File → Open Folder**, then open:

`<project folder>\Gatewell_Parts_Desk\gatewell_app`

Open `gatewell_app` itself, not the folder above it. Claude Code reads its project rules from `CLAUDE.md` in the folder you open.

## 2. One-time setup (VS Code terminal: Terminal → New Terminal)

```powershell
python --version                  # needs 3.11 or newer; install from python.org if missing
copy .env.example .env
notepad .env                      # paste your key after OPENROUTER_API_KEY=, save, close
.\run.bat                         # first run creates .venv and installs packages
```

Then open http://localhost:8000 and sign in as any employee. Stop the app with **Ctrl+C**.

Run the tests (37 should pass):

```powershell
.\.venv\Scripts\python -m pytest tests
```

## 3. Put it in Git (before any changes)

```powershell
git init
git add .
git commit -m "Gatewell Parts Desk starter"
```

Then use VS Code's Source Control panel → **Publish Branch** → choose a **private** repository. `.env` is excluded by `.gitignore`, so your key is never committed.

## 4. First prompt for Claude Code

Open Claude Code (the Claude icon in the sidebar) and paste:

> Read CLAUDE.md, README.md, docs/ARCHITECTURE.md and docs/NEXT_STEPS.md. Then run the test suite with `.venv\Scripts\python -m pytest tests` and confirm all 37 pass. Summarize in a few lines what the project is, what's built, and the security rules you must follow. Don't change any files yet. Then we'll start Step 1 in docs/NEXT_STEPS.md: testing the assistant with my real OpenRouter key.

## 5. Then follow `docs/NEXT_STEPS.md`

- **One step per conversation.**
- **Plan mode for security-related changes:** `auth.py`, `assistant.py`, `db.py`, or sign-on.
- **Review the changes,** run the tests, and commit after each step that works.

**Tip:** to reset the demo's 5-question counter while testing, delete `logs\demo_usage.db`, or set `GATEWELL_DEMO_MODE=0` in `.env`.
