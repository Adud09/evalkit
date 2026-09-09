"""evalkit CLI.

    evalkit run  <solution.py> <suite.json>          run and score
    evalkit check <solution.py> <suite.json>         full report
    evalkit rank <r1.json> <r2.json> ...             leaderboard
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .anticheat import scan_solution, verdict
from .determinism import check_determinism
from .leaderboard import load_leaderboard
from .overfit import check_overfit
from .runner import load_suite, run_solution


def _print_header(title: str) -> None:
    print(f"\n== {title} " + "=" * max(0, 60 - len(title)))


def cmd_run(args: argparse.Namespace) -> int:
    cases = load_suite(args.suite)
    report = run_solution(args.solution, cases, timeout_s=args.timeout)

    _print_header(f"RUN: {Path(args.solution).name}")
    for r in report.results:
        mark = "PASS" if r.passed else r.status.upper()
        print(f"  [{mark:>7}] {r.name:<30} {r.duration_ms:8.1f} ms")
    print(
        f"\n  score: {report.passed_count}/{report.total} "
        f"({report.score:.1%})  avg runtime: {report.avg_runtime_ms:.1f} ms "
        f" peak mem: {report.peak_memory_kb / 1024:.1f} MB"
    )

    if args.output:
        Path(args.output).write_text(json.dumps(report.to_dict(), indent=2))
        print(f"  results written to {args.output}")
    return 0 if report.all_passed else 1


def cmd_check(args: argparse.Namespace) -> int:
    cases = load_suite(args.suite)
    solution = args.solution

    # 1. correctness
    report = run_solution(solution, cases, timeout_s=args.timeout)
    _print_header("CORRECTNESS")
    for r in report.results:
        mark = "PASS" if r.passed else r.status.upper()
        print(f"  [{mark:>7}] {r.name}")
    print(f"  score: {report.score:.1%}")

    # 2. determinism (only meaningful if the solution passes at all)
    _print_header("DETERMINISM")
    if report.score == 0.0:
        print("  skipped (solution scored 0, fix correctness first)")
        det = None
    else:
        det = check_determinism(
            solution, cases, runs=args.determinism_runs, timeout_s=args.timeout
        )
        status = "DETERMINISTIC" if det.is_deterministic else "UNSTABLE"
        print(f"  {status} across {det.runs} shuffled runs")
        for name in det.order_dependent:
            print(f"    ! order-dependent: {name}")
        for name in det.nondeterministic:
            print(f"    ! nondeterministic output: {name}")

    # 3. overfitting
    _print_header("OVERFIT")
    if report.score == 0.0 or len(cases) <= 3:
        print("  skipped (not enough tests or solution scored 0)")
        over = None
    else:
        over = check_overfit(solution, cases, timeout_s=args.timeout)
        flagged = "OVERFIT" if over.is_overfit else "OK"
        print(
            f"  train: {over.train_score:.1%}  val: {over.val_score:.1%}  "
            f"gap: {over.gap:.1%}  -> {flagged}"
        )

    # 4. anticheat
    _print_header("ANTICHEAT")
    expected = [c.stdout.strip() for c in cases if c.stdout.strip()]
    findings = scan_solution(solution, expected_outputs=expected)
    if not findings:
        print("  clean")
    else:
        for f in findings:
            print(f"  [{f.severity.value.upper():<6}] line {f.line:<4} {f.rule}: {f.detail}")
    v = verdict(findings)
    print(f"  verdict: {v}")

    # final summary
    _print_header("SUMMARY")
    checks = {
        "correctness": report.all_passed,
        "determinism": det.is_deterministic if det else True,
        "overfit": not (over and over.is_overfit),
        "anticheat": v != "reject",
    }
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    overall = all(checks.values())
    print(f"\n  OVERALL: {'ACCEPT' if overall else 'REJECT'}")
    return 0 if overall else 1


def cmd_rank(args: argparse.Namespace) -> int:
    board = load_leaderboard(args.results)
    _print_header("LEADERBOARD")
    print(board.render(top=args.top))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evalkit",
        description="Deterministic, anti-cheat code evaluation harness",
    )
    parser.add_argument("--version", action="version", version=f"evalkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a solution against a test suite")
    run.add_argument("solution", help="path to solution .py file")
    run.add_argument("suite", help="path to test suite .json")
    run.add_argument("--timeout", type=float, default=5.0, help="per-test timeout (s)")
    run.add_argument("--output", "-o", help="write result JSON to this path")
    run.set_defaults(func=cmd_run)

    check = sub.add_parser("check", help="full evaluation report")
    check.add_argument("solution", help="path to solution .py file")
    check.add_argument("suite", help="path to test suite .json")
    check.add_argument("--timeout", type=float, default=5.0)
    check.add_argument("--determinism-runs", type=int, default=3)
    check.set_defaults(func=cmd_check)

    rank = sub.add_parser("rank", help="rank result JSON files")
    rank.add_argument("results", nargs="+", help="result JSON files")
    rank.add_argument("--top", type=int, default=None, help="show only top N")
    rank.set_defaults(func=cmd_rank)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
