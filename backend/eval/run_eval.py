"""Run the eval set through the real pipeline and print a score table.

Usage (from backend/):  .venv/Scripts/python eval/run_eval.py [--record "note"] [--only id1,id2]

A question is correct when an expected source (title, and page or timestamp range when given)
is among the cited sources. Out-of-scope questions are correct when refused. Nothing is saved
to answers/unanswered (save=False). --record appends the score row to docs/memory.md §5.
"""

import argparse
import asyncio
import json
import statistics
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app import db
from app.rag import answerer

QUESTIONS = Path(__file__).with_name("questions.json")
MEMORY = BACKEND.parent / "docs" / "memory.md"


def course_ids() -> dict[str, str]:
    rows = db.get_client().table("courses").select("id, code").execute().data
    return {r["code"]: r["id"] for r in rows}


def matches(source: dict[str, Any], expect: dict[str, Any]) -> bool:
    if source.get("title") != expect["title"]:
        return False
    if "page" in expect and source.get("page") != expect["page"]:
        return False
    if "start_s" in expect:
        lo, hi = expect["start_s"]
        start = source.get("start_s")
        if start is None or not lo <= start <= hi:
            return False
    return True


async def run_one(q: dict[str, Any], courses: dict[str, str]) -> dict[str, Any]:
    kwargs = {"scope": q.get("scope", "all"), "course_id": courses.get(q.get("course", "")), "save": False}
    passages, best = await answerer._find_passages(q["question"], kwargs["scope"], kwargs["course_id"], None, None)
    result = await answerer.answer_once(q["question"], **kwargs)
    expect = q["expect"]
    if expect == "refuse":
        ok = result["not_found"]
        rank = None
    else:
        ok = any(matches(s, e) for s in result["sources"] for e in expect)
        rank = next((i + 1 for i, p in enumerate(passages) if any(matches(p, e) for e in expect)), None)
    return {
        "id": q["id"],
        "ok": ok,
        "refuse": expect == "refuse",
        "best": best,
        "rank": rank,
        "first": result["first_token_s"],
        "total": result["total_s"],
        "cited": [f"{s['title'][:28]}{' p' + str(s['page']) if s.get('page') else ''}" for s in result["sources"]],
        "not_found": result["not_found"],
        "error": result["error"],
        "answer": result["answer"],
    }


def commit_hash() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True, cwd=BACKEND
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "?"


def record(row: str) -> None:
    text = MEMORY.read_text(encoding="utf-8")
    header = "| --- | --- | --- | --- | --- | --- | --- |\n"
    anchor = text.index("## 5. Eval scores")
    pos = text.index(header, anchor) + len(header)
    MEMORY.write_text(text[:pos] + row + "\n" + text[pos:], encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", metavar="NOTE", help="append the score row to docs/memory.md")
    parser.add_argument("--only", help="comma-separated question ids")
    parser.add_argument("--verbose", action="store_true", help="print every answer")
    args = parser.parse_args()

    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    if args.only:
        wanted = set(args.only.split(","))
        questions = [q for q in questions if q["id"] in wanted]
    courses = course_ids()

    results = []
    for q in questions:
        r = await run_one(q, courses)
        results.append(r)
        mark = "PASS" if r["ok"] else "FAIL"
        first = f"{r['first']:.1f}s" if r["first"] else "  -  "
        outcome = "refused" if r["not_found"] else (r["error"] or ", ".join(r["cited"]))
        print(f"{mark}  {r['id']:<20} best {r['best']:.3f}  rank {r['rank'] or '-'!s:>2}  {first:>6}  {outcome}")
        if args.verbose or not r["ok"]:
            print(f"      → {r['answer'][:300]}")

    answerable = [r for r in results if not r["refuse"]]
    refusals = [r for r in results if r["refuse"]]
    correct = sum(r["ok"] for r in answerable)
    refused = sum(r["ok"] for r in refusals)
    firsts = [r["first"] for r in results if r["first"]]
    median_first = statistics.median(firsts) if firsts else 0.0
    print(
        f"\nCorrect {correct}/{len(answerable)} · Refused {refused}/{len(refusals)} · "
        f"first token median {median_first:.1f}s, max {max(firsts, default=0):.1f}s"
    )

    if args.record:
        row = (
            f"| {date.today().isoformat()} | {commit_hash()} | {correct}/{len(answerable)} | "
            f"{refused}/{len(refusals)} | — | {median_first:.1f} s median | {args.record} |"
        )
        record(row)
        print("Recorded in docs/memory.md")


if __name__ == "__main__":
    asyncio.run(main())
