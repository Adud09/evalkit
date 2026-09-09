"""Subprocess execution of candidate solutions.

Each test gets its own subprocess with a wall-clock timeout, so a
crashing or hanging submission can't take the grader down with it.
"""

from __future__ import annotations

import json
import random
import resource
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TIMEOUT_S = 5.0


def _child_peak_kb() -> int:
    # ru_maxrss across reaped children. KB on linux, bytes on macos.
    # linux box, not going to pretend otherwise.
    return resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss


@dataclass
class TestCase:
    # not a pytest test class, despite the name
    __test__ = False

    name: str
    stdin: str
    stdout: str

    @classmethod
    def from_dict(cls, d: dict) -> "TestCase":
        return cls(name=d["name"], stdin=d["stdin"], stdout=d["stdout"])


@dataclass
class TestResult:
    name: str
    passed: bool
    status: str  # pass | fail | timeout | error
    duration_ms: float = 0.0
    output: str = ""
    error: str = ""


@dataclass
class RunReport:
    solution: str
    results: list[TestResult] = field(default_factory=list)
    peak_memory_kb: float = 0.0

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def score(self) -> float:
        return self.passed_count / self.total if self.total else 0.0

    @property
    def avg_runtime_ms(self) -> float:
        return (
            sum(r.duration_ms for r in self.results) / len(self.results)
            if self.results
            else 0.0
        )

    @property
    def all_passed(self) -> bool:
        return self.total > 0 and self.passed_count == self.total

    def to_dict(self) -> dict:
        return {
            "solution": self.solution,
            "score": round(self.score, 4),
            "passed": self.passed_count,
            "total": self.total,
            "avg_runtime_ms": round(self.avg_runtime_ms, 2),
            "peak_memory_kb": round(self.peak_memory_kb, 1),
            "results": [
                {
                    "name": r.name,
                    "status": r.status,
                    "duration_ms": round(r.duration_ms, 2),
                }
                for r in self.results
            ],
        }


def run_one(
    solution_path: Path | str,
    case: TestCase,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> TestResult:
    solution_path = Path(solution_path)
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, str(solution_path)],
            input=case.stdin,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        duration_ms = (time.perf_counter() - start) * 1000
        actual = proc.stdout.strip()
        expected = case.stdout.strip()

        if proc.returncode != 0:
            return TestResult(
                name=case.name,
                passed=False,
                status="error",
                duration_ms=duration_ms,
                output=actual,
                error=proc.stderr.strip()[-500:],
            )
        passed = actual == expected
        return TestResult(
            name=case.name,
            passed=passed,
            status="pass" if passed else "fail",
            duration_ms=duration_ms,
            output=actual,
        )
    except subprocess.TimeoutExpired:
        duration_ms = (time.perf_counter() - start) * 1000
        return TestResult(
            name=case.name,
            passed=False,
            status="timeout",
            duration_ms=duration_ms,
            error=f"exceeded {timeout_s}s wall clock",
        )


def run_solution(
    solution_path: Path | str,
    cases: list[TestCase],
    timeout_s: float = DEFAULT_TIMEOUT_S,
    shuffle_seed: int | None = None,
) -> RunReport:
    """Run a solution against the full suite.

    shuffle_seed reruns the tests in a seeded shuffled order. That's
    what the determinism check uses.
    """
    ordered = list(cases)
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(ordered)

    report = RunReport(solution=str(solution_path))
    for case in ordered:
        report.results.append(run_one(solution_path, case, timeout_s))

    # RUSAGE_CHILDREN is a high-water mark over every child this process
    # has ever reaped, so if an earlier run peaked higher, we can't see
    # this run's true peak. Fine for ranking, don't build a billing
    # system on it.
    report.peak_memory_kb = float(_child_peak_kb())
    return report


def load_suite(path: Path | str) -> list[TestCase]:
    """Load a suite from JSON.

    {"test_cases": [{"name": ..., "stdin": ..., "stdout": ...}]}
    """
    data = json.loads(Path(path).read_text())
    return [TestCase.from_dict(d) for d in data["test_cases"]]
