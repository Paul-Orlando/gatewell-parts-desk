"""
Run the assistant evaluation set (tests/eval/questions.yaml) against the live model.

This calls the real OpenRouter API, so it costs money and is kept out of the normal pytest run
(pytest only collects test_*.py). Each question is asked as the employee named in the file,
through assistant.chat(), with the same role-based tools, scope and redaction as the app.

    .venv\\Scripts\\python tests\\eval\\run_eval.py                      # all 60 questions
    .venv\\Scripts\\python tests\\eval\\run_eval.py --only fit-01 tax-01  # a few questions
    .venv\\Scripts\\python tests\\eval\\run_eval.py --category restricted
    .venv\\Scripts\\python tests\\eval\\run_eval.py --model google/gemini-3.1-flash   # compare a model

The key comes from OPENROUTER_API_KEY, or from .env if it isn't set. Results are written to
logs/eval/results-<time>.json, and the audit entries for eval runs go to logs/eval/ so they don't
mix with real usage. Exit code 1 if any question fails (known issues excepted).
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def load_env_file():
    """Set variables from .env that aren't already set (same rule as run.bat). Values are never printed."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip())


# --------------------------------------------------------------------------- grading
def norm(s: str) -> str:
    s = (s or "").lower()
    for a, b in (("’", "'"), ("‘", "'"), ("–", "-"), ("—", "-"), ("−", "-"), (" ", " ")):
        s = s.replace(a, b)
    s = s.replace(",", "").replace("$", "")
    return re.sub(r"\s+", " ", s)


NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
INTERNAL_NAMES: list[str] = []      # tool and analytics section names, set in main(); no reply may contain them
ASKS_BACK = re.compile(r"\?|let me know (which|what)|please (confirm|tell me|specify)|which (engine|one|year|warehouse) ")


def contains(reply: str, fact: str) -> bool:
    """Numbers and short codes must match whole (so '8' isn't found in 'SO-029618' and 'ORD' isn't found
    in 'order'); longer text matches anywhere."""
    r, f = norm(reply), norm(str(fact))
    if NUMBER.match(f):
        return re.search(rf"(?<![\d.]){re.escape(f)}(?!\d)", r) is not None
    if len(f) <= 4:
        return re.search(rf"(?<![a-z0-9]){re.escape(f)}(?![a-z0-9])", r) is not None
    return f in r


def grade(item: dict, reply: str, tools: list[dict], handoff: bool, first_reply: str) -> list[str]:
    """Return the reasons a question failed (empty list = pass)."""
    exp, problems = item.get("expect", {}), []
    for options in exp.get("include", []):
        if not any(contains(reply, o) for o in options):
            problems.append("missing: " + " | ".join(map(str, options)))
    for bad in exp.get("exclude", []):
        if contains(reply, bad):
            problems.append(f"should not contain: {bad}")
    used = [t["tool"] for t in tools if t.get("ok")]
    if exp.get("tools_any") and not set(used) & set(exp["tools_any"]):
        problems.append(f"expected a call to one of {exp['tools_any']}, got {used or 'none'}")
    if "handoff" in exp and bool(handoff) != exp["handoff"]:
        problems.append("expected a handoff to a person" if exp["handoff"] else "unexpected handoff")
    if exp.get("asks_followup") and not ASKS_BACK.search(norm(first_reply)):
        problems.append("expected a follow-up question")
    if "max_tool_calls" in exp and len(tools) > exp["max_tool_calls"]:
        problems.append(f"too many tool calls ({len(tools)} > {exp['max_tool_calls']})")
    leaked = [n for n in INTERNAL_NAMES if n in reply]
    if leaked:
        problems.append(f"mentions internal names: {', '.join(leaked)}")
    return problems


# --------------------------------------------------------------------------- run
class RecordingClient:
    """Wraps the real client to add up token usage and cost reported by OpenRouter."""

    def __init__(self, inner):
        self.inner, self.usage = inner, {}

    def complete(self, payload):
        data = self.inner.complete(payload)
        for k, v in (data.get("usage") or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                self.usage[k] = self.usage.get(k, 0) + v
        return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", metavar="ID", help="question ids to run")
    ap.add_argument("--category", help="run one category")
    ap.add_argument("--model", help="override GATEWELL_MODEL for this run")
    ap.add_argument("--questions", default=str(EVAL_DIR / "questions.yaml"))
    args = ap.parse_args()

    load_env_file()
    if args.model:
        os.environ["GATEWELL_MODEL"] = args.model
    log_dir = ROOT / "logs" / "eval"
    os.environ["GATEWELL_LOG_DIR"] = str(log_dir)       # keep eval traffic out of the real audit log
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY isn't set (and not found in .env). Nothing was run.")
        return 2

    import yaml
    from app import analytics, assistant
    from app.auth import load_employee
    INTERNAL_NAMES[:] = [t["name"] for t in assistant.TOOLS] + list(analytics.SECTIONS)

    items = yaml.safe_load(Path(args.questions).read_text(encoding="utf-8"))
    if args.only:
        items = [i for i in items if i["id"] in args.only]
    if args.category:
        items = [i for i in items if i["category"] == args.category]
    if not items:
        print("No questions match.")
        return 2

    client = RecordingClient(assistant.OpenRouterClient(os.environ["OPENROUTER_API_KEY"]))
    print(f"Model: {assistant.MODEL}   Questions: {len(items)}\n")
    results, started = [], time.time()
    for item in items:
        emp = load_employee(item["employee"])
        turns = item.get("turns") or [item["question"]]
        before = dict(client.usage)
        history, tools, handoff, replies, error = [], [], False, [], None
        t0 = time.time()
        try:
            for text in turns:
                history.append({"role": "user", "content": text})
                out = assistant.chat(emp, history, client=client)
                history.append({"role": "assistant", "content": out["reply"]})
                replies.append(out["reply"])
                tools += out["tools_used"]
                handoff = handoff or bool(out["handoff"])
        except assistant.AssistantUnavailable as ex:
            error = str(ex)
        reply = replies[-1] if replies else ""
        problems = [f"error: {error}"] if error else grade(item, reply, tools, handoff, replies[0] if replies else "")
        cost = client.usage.get("cost", 0) - before.get("cost", 0)
        status = "PASS" if not problems else ("KNOWN" if item.get("known_issue") else "FAIL")
        results.append(dict(id=item["id"], category=item["category"], role=item["role"], status=status,
                            problems=problems, tools=[t["tool"] for t in tools], handoff=handoff,
                            seconds=round(time.time() - t0, 1), cost_usd=round(cost, 6), turns=turns, reply=reply,
                            known_issue=item.get("known_issue")))
        print(f"{status:5} {item['id']:7} {item['role'][:24]:24} {results[-1]['seconds']:5.1f}s  " +
              ("; ".join(problems)[:160] if problems else ""))
        if error and "API key" in error:
            break

    # ---------------------------------------------------------------- summary
    n = len(results)
    passed = sum(r["status"] == "PASS" for r in results)
    known = sum(r["status"] == "KNOWN" for r in results)
    scored = n - known
    print(f"\nAccuracy: {passed}/{n} = {passed / n:.0%}" +
          (f"   (excluding {known} known issue{'s' if known != 1 else ''}: {passed}/{scored} = {passed / scored:.0%})"
           if known and scored else ""))
    cats = {}
    for r in results:
        c = cats.setdefault(r["category"], [0, 0])
        c[0] += r["status"] == "PASS"; c[1] += 1
    print("By category: " + ", ".join(f"{k} {p}/{t}" for k, (p, t) in cats.items()))
    u = client.usage
    cost = u.get("cost")
    print(f"Tokens: {int(u.get('prompt_tokens', 0)):,} in, {int(u.get('completion_tokens', 0)):,} out" +
          (f"   Cost: ${cost:.4f} (${cost / n:.5f} per question)" if cost is not None else
           "   Cost: not reported by the provider") + f"   Time: {time.time() - started:.0f}s")

    log_dir.mkdir(parents=True, exist_ok=True)
    out = log_dir / f"results-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(dict(model=assistant.MODEL, run_at=datetime.now(timezone.utc).isoformat(), accuracy=passed / n,
                                   passed=passed, known_issues=known, total=n, usage=u, results=results),
                              indent=2, default=str), encoding="utf-8")
    print(f"Details: {out.relative_to(ROOT)}")
    return 0 if passed + known == n else 1


if __name__ == "__main__":
    sys.exit(main())
