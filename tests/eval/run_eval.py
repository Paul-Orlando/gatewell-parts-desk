"""
Assistant evaluation runner (docs/EVIDENCE_PLAN.md, Phase B).

Asks every question in tests/eval/questions.yaml through assistant.chat(), as the employee named in the file, with
the same role-based tools, scope and redaction as the app. This calls the real model, so it costs money; it is a
script, not a test, and pytest doesn't collect it. tests/test_eval_set.py checks the questions' facts for free.

    .venv\\Scripts\\python tests\\eval\\run_eval.py --limit 3 --runs 1     # smoke test, about $0.01
    .venv\\Scripts\\python tests\\eval\\run_eval.py                        # all 50 questions x 3 runs
    .venv\\Scripts\\python tests\\eval\\run_eval.py --group restricted
    .venv\\Scripts\\python tests\\eval\\run_eval.py --only ana-01 shp-08
    .venv\\Scripts\\python tests\\eval\\run_eval.py --model google/gemini-3.1-flash --price-in 0.5 --price-out 3

The API key comes from OPENROUTER_API_KEY in the environment, as in the app; this script never reads .env. The demo
limit is switched off for the run, and audit entries go to logs/eval/ so they stay out of the real audit log.

A run passes when all four checks pass: facts (every expected fact and wording present, nothing forbidden), tools
(at least one expected tool called), handoff (to the right team, or none), refusal (declines when it should, and
only then). Runs with more than 3 tool calls or 8 seconds are flagged, not failed.

Results: tests/eval/results/<date>_<model>.csv (one row per run) and .md (summary and failures).
"""
import argparse
import csv
import json
import math
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVAL_DIR / "results"
LOG_DIR = ROOT / "logs" / "eval"
sys.path.insert(0, str(ROOT))

# USD per 1M tokens (input, output). Override with --price-in / --price-out.
PRICES = {
    "google/gemini-3.1-flash-lite": (0.25, 1.50),
}
MAX_TOOL_CALLS, MAX_SECONDS = 3, 8.0

REFUSAL = re.compile(
    r"(doesn't|does not|don't|do not) have access|(isn't|is not|aren't|are not) (available|visible) (to|for) your role"
    r"|your role (doesn't|does not|can't|cannot)|not (able|allowed|permitted) to (see|share|view|show|provide|reveal)"
    r"|(can't|cannot|can not|unable to) (see|share|show|reveal|provide|give you|access|view) (that|this|those|the|our|cost|customer|price|margin|revenue)"
    r"|only (help|assist) with|(can't|cannot|unable to) help with (that|this|requests|anything)|outside (of )?(my|what i|the scope)"
    r"|not something i can (help|do|assist)|i can only|i'm (here|only able) to help with|isn't something i can"
    r"|(can't|cannot|can not) fulfill|(can't|cannot|can not|unable to|not able to) assist with (that|this|requests)"
    r"|(supervisor|manager)s? (or (a )?(supervisor|manager) )?can (get|see|pull|find|run)"
    r"|(can't|cannot|can not|unable to|not able to) (provide|give|share|disclose|reveal|show)( you)?( [a-z-]+){0,3} "
    r"(costs?|margins?|customers?|customer names|prices?|pricing|revenue|totals?)\b")


# --------------------------------------------------------------------------- secrets
_KEYLIKE = re.compile(r"(Bearer\s+)\S+|sk-or-[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{16,}", re.I)


def scrub(text) -> str:
    """Remove the API key, and anything that looks like a key or an Authorization header, from text we print or save."""
    s = str(text or "")
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        s = s.replace(key, "[key removed]")
    return _KEYLIKE.sub(lambda m: (m.group(1) or "") + "[key removed]", s)


# --------------------------------------------------------------------------- grading
def norm(s) -> str:
    s = str(s or "").lower()
    for a, b in (("’", "'"), ("‘", "'"), ("–", "-"), ("—", "-"), ("−", "-"), (" ", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s.replace(",", "").replace("$", ""))


NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def contains(reply: str, value) -> bool:
    """Numbers and short codes match whole ('8' isn't found in 'SO-029618'); punctuation and longer text match anywhere."""
    r, f = norm(reply), norm(value)
    if not re.search(r"[a-z0-9]", f):
        return f in r
    if NUMBER.match(f):
        return re.search(rf"(?<![\d.]){re.escape(f)}(?!\d)", r) is not None
    if len(f) <= 4:
        return re.search(rf"(?<![a-z0-9]){re.escape(f)}(?![a-z0-9])", r) is not None
    return f in r


def options(entry) -> list:
    return entry if isinstance(entry, list) else [entry]


def grade(q: dict, reply: str, tools: list[dict], handoff: dict | None) -> dict:
    """The four Phase B checks: each is '' (pass) or the reason it failed."""
    used = [t["tool"] for t in tools if t.get("ok")]
    words = (q.get("expect_facts") or []) + (q.get("expect_words") or [])
    cond = q.get("when_not_called")
    if cond and not set(used) & set(cond["tools"]):
        words = words + cond["expect_words"]       # e.g. an FAQ-only answer must state the rule exactly
    missing = [" | ".join(map(str, options(e))) for e in words if not any(contains(reply, o) for o in options(e))]
    bad = [str(f) for f in q.get("forbid") or [] if contains(reply, f)]
    facts = "; ".join(([f"missing: {', '.join(missing)}"] if missing else []) +
                      ([f"should not contain: {', '.join(bad)}"] if bad else []))
    want = q.get("expect_tools") or []
    tool = "" if not want or set(used) & set(want) else f"expected one of {want}, called {used or 'nothing'}"
    got_dept = (handoff or {}).get("department_id")
    if q["expect_handoff"] and q.get("handoff_optional") and not handoff:
        hand = ""                               # giving the team's contacts without a handoff is also right
    elif q["expect_handoff"]:
        hand = "" if got_dept == q["expect_handoff"] else f"expected a handoff to {q['expect_handoff']}, got {got_dept or 'none'}"
    else:
        hand = "" if not handoff else f"unexpected handoff to {got_dept}"
    declined = bool(REFUSAL.search(norm(reply)))
    refusal = "" if declined == q["expect_refusal"] else ("expected a refusal" if q["expect_refusal"] else "refused when it shouldn't")
    return {"facts": facts, "tools": tool, "handoff": hand, "refusal": refusal}


# --------------------------------------------------------------------------- run
def audit_tokens(path: Path, start: int) -> dict:
    """Add up the token counts the assistant wrote to its audit log after byte offset 'start'."""
    totals = {}
    if not path.exists():
        return totals
    with open(path, "rb") as f:
        f.seek(start)
        for line in f.read().decode("utf-8", "replace").splitlines():
            try:
                usage = json.loads(line).get("tokens") or {}
            except json.JSONDecodeError:
                continue
            for k, v in usage.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    totals[k] = totals.get(k, 0) + v
    return totals


def ask(assistant, emp, q, audit_path):
    turns = q.get("turns") or [q["question"]]
    start = audit_path.stat().st_size if audit_path.exists() else 0
    history, tools, handoff, reply, error, grounding = [], [], None, "", "", ""
    t0 = time.time()
    try:
        for text in turns:
            history.append({"role": "user", "content": text})
            out = assistant.chat(emp, history, client=None)
            reply = out["reply"]
            history.append({"role": "assistant", "content": reply})
            tools += out["tools_used"]
            handoff = out["handoff"] or handoff
            grounding = out.get("grounding") or grounding
    except assistant.AssistantUnavailable as ex:
        error = scrub(ex)
    return dict(reply=reply, tools=tools, handoff=handoff, error=error, grounding=grounding, seconds=round(time.time() - t0, 2),
                usage=audit_tokens(audit_path, start))


def p95(values):
    v = sorted(values)
    return v[min(len(v) - 1, math.ceil(0.95 * len(v)) - 1)] if v else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=3, help="runs per question (default 3)")
    ap.add_argument("--limit", type=int, help="only the first N questions (after --only / --group)")
    ap.add_argument("--only", nargs="+", metavar="ID", help="question ids")
    ap.add_argument("--group", help="one group: stock, orders, shipping, international, analytics, restricted, handoffs")
    ap.add_argument("--model", help="model id (default: GATEWELL_MODEL, else the app's default)")
    ap.add_argument("--price-in", type=float, help="USD per 1M input tokens")
    ap.add_argument("--price-out", type=float, help="USD per 1M output tokens")
    ap.add_argument("--questions", default=str(EVAL_DIR / "questions.yaml"))
    ap.add_argument("--rescore", metavar="CSV", help="re-score the saved answers in a results CSV with today's questions.yaml "
                                                     "(no model calls); writes <name>_rescored.csv and .md")
    args = ap.parse_args()

    # Before the app is imported: demo limit off, eval audit log, chosen model.
    os.environ["GATEWELL_DEMO_MODE"] = "0"
    os.environ["GATEWELL_LOG_DIR"] = str(LOG_DIR)
    if args.model:
        os.environ["GATEWELL_MODEL"] = args.model
    if args.rescore:
        return rescore(Path(args.rescore), Path(args.questions))
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY isn't set in this terminal, so nothing was run.\n"
              "Set it for this session first (this script never reads .env), then run again.")
        return 2

    import yaml
    from app import analytics, assistant
    from app.auth import load_employee

    items = yaml.safe_load(Path(args.questions).read_text(encoding="utf-8"))
    if args.only:
        items = [q for q in items if q["id"] in args.only]
    if args.group:
        items = [q for q in items if q["group"] == args.group]
    if args.limit:
        items = items[:args.limit]
    if not items:
        print("No questions match.")
        return 2

    model = assistant.MODEL
    p_in, p_out = PRICES.get(model, (None, None))
    p_in, p_out = args.price_in if args.price_in is not None else p_in, args.price_out if args.price_out is not None else p_out
    internal = [t["name"] for t in assistant.TOOLS] + list(analytics.SECTIONS)
    audit_path = LOG_DIR / "assistant_audit.jsonl"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Model: {model}   Questions: {len(items)}   Runs each: {args.runs}"
          + (f"   Prices: ${p_in}/${p_out} per 1M tokens" if p_in is not None else "   Prices: unknown (pass --price-in/--price-out)"))
    rows, started = [], time.time()
    for q in items:
        emp = load_employee(q["employee_id"])
        for run in range(1, args.runs + 1):
            r = ask(assistant, emp, q, audit_path)
            checks = {"facts": f"error: {r['error']}", "tools": "", "handoff": "", "refusal": ""} if r["error"] else \
                grade(q, r["reply"], r["tools"], r["handoff"])
            tin, tout = int(r["usage"].get("prompt_tokens", 0)), int(r["usage"].get("completion_tokens", 0))
            cost = (tin * p_in + tout * p_out) / 1e6 if p_in is not None else None
            flags = ([f"{len(r['tools'])} tool calls"] if len(r["tools"]) > MAX_TOOL_CALLS else []) + \
                    ([f"{r['seconds']:.1f} s"] if r["seconds"] > MAX_SECONDS else []) + \
                    [f"mentions internal name {n}" for n in internal if n in r["reply"]]
            passed = not any(checks.values())
            rows.append(dict(id=q["id"], group=q["group"], employee_id=q["employee_id"], run=run,
                             passed=passed, facts_ok=not checks["facts"], tools_ok=not checks["tools"],
                             handoff_ok=not checks["handoff"], refusal_ok=not checks["refusal"],
                             expect_refusal=q["expect_refusal"], seconds=r["seconds"], tool_calls=len(r["tools"]),
                             tools_used=" ".join(t["tool"] for t in r["tools"]),
                             handoff_department=(r["handoff"] or {}).get("department_id") or "",
                             grounding=r["grounding"],
                             input_tokens=tin, output_tokens=tout,
                             cost_usd=round(cost, 6) if cost is not None else "",
                             problems=scrub("; ".join(f"{k}: {v}" for k, v in checks.items() if v)),
                             flags="; ".join(flags), question=q.get("question") or " / ".join(q["turns"]), reply=scrub(r["reply"])))
            print(f"{'PASS' if passed else 'FAIL'} {q['id']:7} run {run}  {r['seconds']:5.1f}s  {len(r['tools'])} tools"
                  + (f"  [{'; '.join(flags)}]" if flags else "") + (f"  {rows[-1]['problems'][:150]}" if not passed else ""))
            if r["error"] and "API key" in r["error"]:
                print("Stopped: the API key was rejected.")
                return 2

    csv_path, md_path = write_results(rows, model, args.runs, cost_known=p_in is not None, elapsed=time.time() - started)
    print(f"\nResults: {csv_path.relative_to(ROOT)} and {md_path.relative_to(ROOT)}")
    return 0 if all(r["passed"] for r in rows) else 1


# --------------------------------------------------------------------------- re-score saved answers
def rescore(path: Path, questions_path: Path) -> int:
    """Grade the answers saved in a results CSV again with today's questions.yaml, without calling the model.
    Time, tool calls, tokens and cost are kept from the original run."""
    import yaml
    from app import analytics, assistant
    qs = {q["id"]: q for q in yaml.safe_load(questions_path.read_text(encoding="utf-8"))}
    internal = [t["name"] for t in assistant.TOOLS] + list(analytics.SECTIONS)
    saved = list(csv.DictReader(open(path, encoding="utf-8")))
    header = (path.with_suffix(".md").read_text(encoding="utf-8").splitlines() or [""])[0] if path.with_suffix(".md").exists() else ""
    model = header.split(": ", 1)[1] if header.startswith("# Assistant evaluation: ") else path.stem
    rows, inferred = [], 0
    for r in saved:
        q = qs[r["id"]]
        used = r["tools_used"].split()
        tools = [{"tool": t, "ok": True} for t in used]
        dept = r.get("handoff_department")
        if dept is None:            # older files didn't save the department: infer it from the original check
            inferred += 1
            dept = "" if "escalate_to_person" not in used else \
                (q["expect_handoff"] if r["handoff_ok"] == "True" and q["expect_handoff"] else "unknown")
        handoff = {"department_id": dept} if dept else None
        if r["problems"].startswith("facts: error:"):
            checks = {"facts": r["problems"][len("facts: "):], "tools": "", "handoff": "", "refusal": ""}
        else:
            checks = grade(q, r["reply"], tools, handoff)
        flags = [f for f in r["flags"].split("; ") if f and not f.startswith("mentions internal name")] + \
                [f"mentions internal name {n}" for n in internal if n in r["reply"]]
        rows.append({**r, "passed": not any(checks.values()), "facts_ok": not checks["facts"],
                     "tools_ok": not checks["tools"], "handoff_ok": not checks["handoff"],
                     "refusal_ok": not checks["refusal"], "expect_refusal": q["expect_refusal"],
                     "handoff_department": dept, "problems": "; ".join(f"{k}: {v}" for k, v in checks.items() if v),
                     "flags": "; ".join(flags), "seconds": float(r["seconds"]), "tool_calls": int(r["tool_calls"]),
                     "cost_usd": float(r["cost_usd"]) if r["cost_usd"] else ""})
    runs = max(int(r["run"]) for r in rows)
    note = (f"Re-scored from {path.name} with today's questions.yaml (no model calls). Time, tool calls and cost are "
            "from the original run." + (" Handoff departments were inferred from the original checks." if inferred else ""))
    csv_path, md_path = write_results(rows, model, runs, cost_known=all(r["cost_usd"] != "" for r in rows),
                                      elapsed=sum(r["seconds"] for r in rows), stem=f"{path.stem}_rescored", note=note)
    print(f"Re-scored {len(rows)} runs: {sum(r['passed'] for r in rows)} passed "
          f"(was {sum(r['passed'] == 'True' for r in saved)}).\nResults: {csv_path.relative_to(ROOT)} and {md_path.relative_to(ROOT)}")
    return 0


# --------------------------------------------------------------------------- outputs
def write_results(rows, model, runs, cost_known, elapsed, stem=None, note=None) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = stem or f"{date.today().isoformat()}_{re.sub(r'[^A-Za-z0-9.-]+', '-', model)}"     # model ids contain dots ("3.1")
    csv_path, md_path = RESULTS_DIR / f"{stem}.csv", RESULTS_DIR / f"{stem}.md"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    qids = list(dict.fromkeys(r["id"] for r in rows))
    by_q = {i: [r for r in rows if r["id"] == i] for i in qids}
    consistent = [i for i in qids if all(r["passed"] for r in by_q[i])]
    refusals = [r for r in rows if r["expect_refusal"]]
    secs = [r["seconds"] for r in rows]
    costs = [r["cost_usd"] for r in rows if r["cost_usd"] != ""]
    pct = lambda a, b: f"{a}/{b} ({a / b:.0%})" if b else "n/a"

    md = [f"# Assistant evaluation: {model}", "",
          f"Run on {date.today():%a, %b %d, %Y}. {len(qids)} questions × {runs} run(s) = {n} runs, {elapsed / 60:.1f} minutes.", "",
          *([note, ""] if note else []),
          "| Measure | Result |", "|---|---|",
          f"| Pass rate (all runs) | {pct(sum(r['passed'] for r in rows), n)} |",
          f"| Consistency (questions that passed every run) | {pct(len(consistent), len(qids))} |",
          f"| Refusal accuracy (runs that should decline) | {pct(sum(r['refusal_ok'] for r in refusals), len(refusals))} |",
          f"| Average time | {sum(secs) / n:.1f} s |", f"| 95th-percentile time | {p95(secs):.1f} s |",
          f"| Average tool calls | {sum(r['tool_calls'] for r in rows) / n:.1f} |"]
    if "grounding" in rows[0]:
        fired = [r.get("grounding") for r in rows if r.get("grounding")]
        md.append(f"| Grounding check fired | {len(fired)}/{n} runs ({fired.count('retried')} retried, "
                  f"{fired.count('blocked')} blocked) |")
    if cost_known and costs:
        md += [f"| Average cost per question (one run) | ${sum(costs) / len(costs):.4f} |",
               f"| Total cost | ${sum(costs):.4f} |"]
    md += ["", "## By group", "", "| Group | Pass rate | Facts | Tools | Handoff | Refusal |", "|---|---|---|---|---|---|"]
    for g in dict.fromkeys(r["group"] for r in rows):
        gr = [r for r in rows if r["group"] == g]
        md.append(f"| {g} | {pct(sum(r['passed'] for r in gr), len(gr))} | " +
                  " | ".join(f"{sum(r[k] for r in gr)}/{len(gr)}" for k in ("facts_ok", "tools_ok", "handoff_ok", "refusal_ok")) + " |")
    flagged = [r for r in rows if r["flags"]]
    md += ["", f"## Flagged runs ({len(flagged)}): more than {MAX_TOOL_CALLS} tool calls or {MAX_SECONDS:.0f} seconds", ""]
    md += [f"- {r['id']} run {r['run']}: {r['flags']}" for r in flagged] or ["None."]
    failed = [r for r in rows if not r["passed"]]
    md += ["", f"## Failures ({len(failed)})", ""]
    for r in failed:
        md += [f"### {r['id']} run {r['run']} ({r['group']}, {r['employee_id']})", "",
               f"**Question:** {r['question']}", "", f"**Why:** {r['problems']}", "",
               f"**Tools:** {r['tools_used'] or 'none'}", "", "**Answer:**", "",
               "> " + (r["reply"] or "(no reply)").replace("\n", "\n> "), ""]
    if not failed:
        md.append("None.")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return csv_path, md_path


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Stopped.")
        sys.exit(130)
    except Exception as ex:      # no traceback: it could include request details. Just the error, with any key removed.
        print(f"The evaluation stopped: {type(ex).__name__}: {scrub(ex)}")
        sys.exit(1)
